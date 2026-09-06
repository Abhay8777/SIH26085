/* ============================================================
   SIH26085 — URBAN FLOOD NOWCASTING
   FRONTEND APPLICATION
   ============================================================ */

"use strict";


/* ============================================================
   API CONFIGURATION
   ============================================================ */

const API_URL = "https://sih-26085-gigm.vercel.app";

const MUMBAI_CENTER = [
    19.0760,
    72.8777
];

const MUMBAI_ZOOM = 12;


/* ============================================================
   RISK COLORS
   ============================================================ */

const RISK_COLORS = {

    low:
        "#22c55e",

    moderate:
        "#eab308",

    high:
        "#f97316",

    severe:
        "#ef4444",

    caution:
        "#eab308",

    dangerous:
        "#ef4444",

    unknown:
        "#64748b"
};


/* ============================================================
   DRAINAGE COLORS
   ============================================================ */

const DRAINAGE_COLORS = {

    within_capacity:
        "#22c55e",

    near_capacity:
        "#eab308",

    over_capacity:
        "#f97316",

    severe_surcharge:
        "#ef4444",

    unknown:
        "#64748b"
};


/* ============================================================
   DEVELOPMENT DRAINAGE NETWORK
   ============================================================ */

const DRAINAGE_EDGES = {

    E1: {
        fromNode:
            "N1",

        toNode:
            "N2",

        from:
            [19.0500, 72.8500],

        to:
            [19.0500, 72.8590]
    },

    E2: {
        fromNode:
            "N2",

        toNode:
            "N3",

        from:
            [19.0500, 72.8590],

        to:
            [19.0590, 72.8590]
    },

    E3: {
        fromNode:
            "N3",

        toNode:
            "N4",

        from:
            [19.0590, 72.8590],

        to:
            [19.0680, 72.8590]
    }
};


const DRAINAGE_NODES = {

    N1:
        [19.0500, 72.8500],

    N2:
        [19.0500, 72.8590],

    N3:
        [19.0590, 72.8590],

    N4:
        [19.0680, 72.8590]
};


/* ============================================================
   GLOBAL LAYER REFERENCES
   ============================================================ */

let floodLayer = null;

let drainageNetworkLayer = null;

let safeRouteLayer = null;

let blockageLayer = null;

let floodForecastChart = null;


/* ============================================================
   MAP INITIALIZATION
   ============================================================ */

const map =
    L.map(
        "map",
        {
            center:
                MUMBAI_CENTER,

            zoom:
                MUMBAI_ZOOM,

            zoomControl:
                true,

            preferCanvas:
                false
        }
    );


/* ============================================================
   BASE MAP
   ============================================================ */

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom:
            19,

        minZoom:
            10,

        attribution:
            "&copy; OpenStreetMap contributors",

        crossOrigin:
            true
    }
).addTo(map);


/* ============================================================
   CUSTOM LEAFLET PANES
   ============================================================ */

function createMapPanes() {

    if (!map.getPane("floodMarkers")) {

        map.createPane(
            "floodMarkers"
        );
    }

    if (!map.getPane("drainageNetwork")) {

        map.createPane(
            "drainageNetwork"
        );
    }

    if (!map.getPane("safeRoute")) {

        map.createPane(
            "safeRoute"
        );
    }

    if (!map.getPane("blockedDrainage")) {

        map.createPane(
            "blockedDrainage"
        );
    }


    map.getPane(
        "floodMarkers"
    ).style.zIndex = 750;


    map.getPane(
        "drainageNetwork"
    ).style.zIndex = 800;


    map.getPane(
        "safeRoute"
    ).style.zIndex = 1000;


    map.getPane(
        "blockedDrainage"
    ).style.zIndex = 1100;


    map.getPane(
        "floodMarkers"
    ).style.pointerEvents = "auto";


    map.getPane(
        "drainageNetwork"
    ).style.pointerEvents = "auto";


    map.getPane(
        "safeRoute"
    ).style.pointerEvents = "auto";


    map.getPane(
        "blockedDrainage"
    ).style.pointerEvents = "auto";
}


createMapPanes();


/* ============================================================
   UTILITY — NORMALIZE RISK
   ============================================================ */

function normalizeRisk(risk) {

    if (
        risk === null ||
        risk === undefined ||
        risk === ""
    ) {

        return null;
    }


    const value =
        String(risk)
            .trim()
            .toLowerCase()
            .replace(
                /[_-]/g,
                " "
            )
            .replace(
                /\s+/g,
                " "
            );


    if (
        value === "low" ||
        value === "low risk"
    ) {

        return "low";
    }


    if (
        value === "moderate" ||
        value === "moderate risk" ||
        value === "medium" ||
        value === "medium risk"
    ) {

        return "moderate";
    }


    if (
        value === "high" ||
        value === "high risk"
    ) {

        return "high";
    }


    if (
        value === "severe" ||
        value === "severe risk" ||
        value === "critical" ||
        value === "critical risk"
    ) {

        return "severe";
    }


    if (
        value === "caution"
    ) {

        return "caution";
    }


    if (
        value === "dangerous"
    ) {

        return "dangerous";
    }


    return null;
}


/* ============================================================
   RISK COLOR
   ============================================================ */

function getRiskColor(risk) {

    const normalized =
        normalizeRisk(risk) ||
        "unknown";


    return (
        RISK_COLORS[
            normalized
        ] ||
        RISK_COLORS.unknown
    );
}


/* ============================================================
   RISK TEXT
   ============================================================ */

function getRiskText(risk) {

    const normalized =
        normalizeRisk(risk);


    if (!normalized) {

        return "UNKNOWN";
    }


    return normalized.toUpperCase();
}


/* ============================================================
   DEPTH → RISK FALLBACK
   ============================================================ */

function getRiskFromDepth(depth) {

    const value =
        Number(depth) || 0;


    /*
       Keep this consistent with backend
       surface_flood_service.py:

       < 2 cm   = low
       < 10 cm  = moderate
       < 20 cm  = high
       >= 20 cm = severe
    */

    if (value < 2.0) {

        return "low";
    }


    if (value < 10.0) {

        return "moderate";
    }


    if (value < 20.0) {

        return "high";
    }


    return "severe";
}


/* ============================================================
   FEATURE RISK
   ============================================================ */

/* ============================================================
   FEATURE RISK
   ============================================================ */

function getFeatureRisk(properties) {

    const depth =
        safeNumber(
            properties?.water_depth_cm
        );

    return {

        risk:
            getRiskFromDepth(
                depth
            ),

        source:
            "Water depth"
    };
}


/* ============================================================
   BACKEND STATUS
   ============================================================ */

function setBackendStatus(online) {

    const status =
        document.getElementById(
            "backend-status"
        );


    const text =
        document.getElementById(
            "backend-status-text"
        );


    if (!status) {

        return;
    }


    if (text) {

        text.textContent =
            online
                ? "Backend Online"
                : "Backend Offline";
    }
    else {

        const spans =
            status.querySelectorAll(
                "span"
            );


        if (spans.length > 1) {

            spans[1].textContent =
                online
                    ? "Backend Online"
                    : "Backend Offline";
        }
    }


    if (online) {

        status.classList.remove(
            "offline"
        );

    }
    else {

        status.classList.add(
            "offline"
        );
    }
}


/* ============================================================
   SAFE NUMBER
   ============================================================ */

function safeNumber(
    value,
    fallback = 0
) {

    const number =
        Number(value);


    return Number.isFinite(
        number
    )
        ? number
        : fallback;
}


/* ============================================================
   FLOOD POPUP
   ============================================================ */

function createFloodPopup(
    properties
) {

    const result =
        getFeatureRisk(
            properties
        );


    const risk =
        result.risk;


    const source =
        result.source;


    const rainfall =
        safeNumber(
            properties?.rainfall_mm
        );


    const runoff =
        safeNumber(
            properties?.runoff_mm
        );


    const depth =
        safeNumber(
            properties?.water_depth_cm
        );


    const elevation =
        safeNumber(
            properties?.elevation_m
        );


    return `
        <div class="flood-popup">

            <div class="popup-title">
                Flood Risk Cell
            </div>

            <div class="popup-row">
                <span>Risk</span>

                <strong
                    style="color:${getRiskColor(risk)};"
                >
                    ${getRiskText(risk)}
                </strong>
            </div>

            <div class="popup-row">
                <span>Rainfall</span>

                <strong>
                    ${rainfall.toFixed(2)} mm
                </strong>
            </div>

            <div class="popup-row">
                <span>Runoff</span>

                <strong>
                    ${runoff.toFixed(2)} mm
                </strong>
            </div>

            <div class="popup-row">
                <span>Water Depth</span>

                <strong>
                    ${depth.toFixed(2)} cm
                </strong>
            </div>

            <div class="popup-row">
                <span>Elevation</span>

                <strong>
                    ${elevation.toFixed(2)} m
                </strong>
            </div>

            <div class="popup-row">
                <span>Grid Cell</span>

                <strong>
                    ${properties?.row ?? "--"},
                    ${properties?.column ?? "--"}
                </strong>
            </div>

            <div class="popup-source">
                Risk source:
                ${source}
            </div>

        </div>
    `;
}


/* ============================================================
   FLOOD TOOLTIP
   ============================================================ */

function createFloodTooltip(
    properties
) {

    const result =
        getFeatureRisk(
            properties
        );


    const risk =
        result.risk;


    return `
        <div class="flood-tooltip">

            <strong>
                ${getRiskText(risk)} RISK
            </strong>

            <br>

            Rainfall:
            ${safeNumber(
                properties?.rainfall_mm
            ).toFixed(2)} mm

            <br>

            Water depth:
            ${safeNumber(
                properties?.water_depth_cm
            ).toFixed(2)} cm

        </div>
    `;
}


/* ============================================================
   CREATE FLOOD MARKER
   ============================================================ */

function createFloodMarker(
    feature,
    latlng
) {

    const properties =
        feature.properties ||
        {};


    const result =
        getFeatureRisk(
            properties
        );


    const risk =
        result.risk;


    const color =
        getRiskColor(
            risk
        );


    const marker =
        L.circleMarker(
            latlng,
            {

                pane:
                    "floodMarkers",

                radius:
                    10,

                fillColor:
                    color,

                fillOpacity:
                    0.95,

                color:
                    "#ffffff",

                weight:
                    3,

                opacity:
                    1
            }
        );


    marker.bindTooltip(
        createFloodTooltip(
            properties
        ),
        {

            direction:
                "top",

            offset:
                [0, -12],

            sticky:
                false,

            opacity:
                1,

            className:
                "flood-hover-tooltip"
        }
    );


    marker.bindPopup(
        createFloodPopup(
            properties
        ),
        {

            maxWidth:
                320,

            closeButton:
                true,

            autoPan:
                true
        }
    );


    marker.on(
        "mouseover",
        function () {

            if (
                !this.isPopupOpen()
            ) {

                this.openTooltip();
            }


            this.setStyle({

                radius:
                    14,

                weight:
                    4,

                fillOpacity:
                    1
            });
        }
    );


    marker.on(
        "mouseout",
        function () {

            this.closeTooltip();


            this.setStyle({

                radius:
                    10,

                weight:
                    3,

                fillOpacity:
                    0.95
            });
        }
    );


    return marker;
}


/* ============================================================
   UPDATE DASHBOARD STATS
   ============================================================ */

function updateStats(
    features,
    properties
) {

    let floodedCells =
        0;


    let maxDepth =
        0;


    const riskCounts = {

        low:
            0,

        moderate:
            0,

        high:
            0,

        severe:
            0
    };


    for (
        const feature of features
    ) {

        const data =
            feature.properties ||
            {};


        const depth =
            safeNumber(
                data.water_depth_cm
            );


        const result =
            getFeatureRisk(
                data
            );


        if (depth > 0) {

            floodedCells++;
        }


        if (
            depth > maxDepth
        ) {

            maxDepth =
                depth;
        }


        if (
            Object.prototype.hasOwnProperty.call(
                riskCounts,
                result.risk
            )
        ) {

            riskCounts[
                result.risk
            ]++;
        }
    }


   let overall =
    getRiskFromDepth(
        maxDepth
    );


    const overallElement =
        document.getElementById(
            "overall-status"
        );


    if (overallElement) {

        overallElement.textContent =
            overall.toUpperCase();

        overallElement.style.color =
            getRiskColor(
                overall
            );
    }


    const depthElement =
        document.getElementById(
            "max-depth"
        );


    if (depthElement) {

        depthElement.textContent =
            `${maxDepth.toFixed(2)} cm`;
    }


    const floodedElement =
        document.getElementById(
            "flooded-cells"
        );


    if (floodedElement) {

        floodedElement.textContent =
            floodedCells;
    }


    const overloadedElement =
        document.getElementById(
            "overloaded-drains"
        );


    if (overloadedElement) {

        overloadedElement.textContent =
            safeNumber(
                properties?.overloaded_drainage_edges
            );
    }


    console.log(
        "SIH26085 Flood Summary:",
        {

            overallStatus:
                overall,

            floodedCells:
                floodedCells,

            maxDepth:
                maxDepth,

            riskCounts:
                riskCounts
        }
    );
}


/* ============================================================
   LOAD FLOOD NOWCAST MAP
   ============================================================ */

async function loadFloodLayer() {

    try {

        const forecastElement =
            document.getElementById(
                "forecast-time"
            );


        const minutesAhead =
            forecastElement
                ? Number(
                    forecastElement.value
                )
                : 0;


        const scenarioElement =
            document.getElementById(
                "scenario-select"
            );


        const scenario =
            scenarioElement
                ? scenarioElement.value
                : "heavy";


        console.log(
            "Loading flood nowcast:",
            scenario,
            minutesAhead
        );


        const response =
            await fetch(

                `${API_URL}/flood/nowcast-map` +
                `?scenario=${encodeURIComponent(
                    scenario
                )}` +
                `&minutes_ahead=${minutesAhead}`,

                {

                    method:
                        "GET",

                    headers:
                        {
                            "Accept":
                                "application/json"
                        },

                    cache:
                        "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `Nowcast API HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        if (
            !data ||
            data.status !== "success" ||
            !data.forecast
        ) {

            throw new Error(
                "Invalid nowcast response"
            );
        }


        const forecast =
            data.forecast;


        const floodCells =
            Array.isArray(
                forecast.flood_cells
            )
                ? forecast.flood_cells
                : [];


        const drainageEdges =
            Array.isArray(
                forecast.drainage_edges
            )
                ? forecast.drainage_edges
                : [];


        /* ----------------------------------------------------
           REMOVE OLD FLOOD LAYER
           ---------------------------------------------------- */

        if (floodLayer) {

            map.removeLayer(
                floodLayer
            );

            floodLayer =
                null;
        }
        

        /* ----------------------------------------------------
   CLEAR OLD BLOCKAGE HIGHLIGHT
   ---------------------------------------------------- */

if (blockageLayer) {

    map.removeLayer(
        blockageLayer
    );

    blockageLayer =
        null;
}

        /* ----------------------------------------------------
           CREATE GEOJSON
           ---------------------------------------------------- */

        /* ----------------------------------------------------
   CREATE FLOOD GRID POLYGONS
   ---------------------------------------------------- */

/*
   Development model uses a 3x3 spatial grid.

   Each flood cell is converted from a point
   into a geographic rectangle so that the
   map displays flood depth spatially.
*/

const CELL_HALF_SIZE_LAT =
    0.0045;

const CELL_HALF_SIZE_LNG =
    0.0045;


const features =
    floodCells.map(
        function (cell) {

            const latitude =
                safeNumber(
                    cell.latitude
                );

            const longitude =
                safeNumber(
                    cell.longitude
                );


            return {

                type:
                    "Feature",

                geometry: {

                    type:
                        "Polygon",

                    coordinates: [[

                        [
                            longitude -
                            CELL_HALF_SIZE_LNG,

                            latitude -
                            CELL_HALF_SIZE_LAT
                        ],

                        [
                            longitude +
                            CELL_HALF_SIZE_LNG,

                            latitude -
                            CELL_HALF_SIZE_LAT
                        ],

                        [
                            longitude +
                            CELL_HALF_SIZE_LNG,

                            latitude +
                            CELL_HALF_SIZE_LAT
                        ],

                        [
                            longitude -
                            CELL_HALF_SIZE_LNG,

                            latitude +
                            CELL_HALF_SIZE_LAT
                        ],

                        [
                            longitude -
                            CELL_HALF_SIZE_LNG,

                            latitude -
                            CELL_HALF_SIZE_LAT
                        ]

                    ]]
                },

                properties:
                    cell
            };
        }
    );


const geoJson = {

    type:
        "FeatureCollection",

    features:
        features
};


/* ----------------------------------------------------
   CREATE FLOOD DEPTH GIS LAYER
   ---------------------------------------------------- */

floodLayer =
    L.geoJSON(
        geoJson,
        {

            pane:
                "floodMarkers",

            style:
                function (feature) {

                    const depth =
                        safeNumber(
                            feature.properties
                                ?.water_depth_cm
                        );


                    return {

                        fillColor:
                            getRiskColor(
                                getRiskFromDepth(
                                    depth
                                )
                            ),

                        fillOpacity:
                            0.48,

                        color:
                            getRiskColor(
                                getRiskFromDepth(
                                    depth
                                )
                            ),

                        weight:
                            1,

                        opacity:
                            0.75
                    };
                },


            onEachFeature:
                function (
                    feature,
                    layer
                ) {

                    const properties =
                        feature.properties ||
                        {};


                    layer.bindTooltip(
                        createFloodTooltip(
                            properties
                        ),
                        {

                            sticky:
                                true,

                            direction:
                                "top",

                            opacity:
                                1,

                            className:
                                "flood-hover-tooltip"
                        }
                    );


                    layer.bindPopup(
                        createFloodPopup(
                            properties
                        ),
                        {

                            maxWidth:
                                320,

                            closeButton:
                                true,

                            autoPan:
                                true
                        }
                    );


                    layer.on(
                        "mouseover",
                        function () {

                            this.setStyle({

                                fillOpacity:
                                    0.68,

                                weight:
                                    2
                            });
                        }
                    );


                    layer.on(
                        "mouseout",
                        function () {

                            this.setStyle({

                                fillOpacity:
                                    0.48,

                                weight:
                                    1
                            });
                        }
                    );
                }
        }
    );


floodLayer.addTo(
    map
);

        /* ----------------------------------------------------
           DRAINAGE STATUS MAP
           ---------------------------------------------------- */

        const drainageStatuses =
            {};


        drainageEdges.forEach(
            function (edge) {

                if (
                    edge &&
                    edge.edge_id
                ) {

                    drainageStatuses[
                        edge.edge_id
                    ] =
                        edge.status ||
                        "unknown";
                }
            }
        );


        /* ----------------------------------------------------
           REDRAW DRAINAGE
           ---------------------------------------------------- */

        drawDrainageNetwork(
            drainageStatuses
        );


        /* ----------------------------------------------------
           UPDATE SIDEBAR
           ---------------------------------------------------- */

        updateStats(
            features,
            {

                overall_status:
                    forecast.risk,

                max_water_depth_cm:
                    forecast.max_water_depth_cm,

                flooded_cells:
                    forecast.flooded_cells,

                overloaded_drainage_edges:
                    forecast.overloaded_drainage_edges
            }
        );


        /* ----------------------------------------------------
           MODEL SOURCE
           ---------------------------------------------------- */

        const sourceElement =
            document.getElementById(
                "model-source"
            );


        if (sourceElement) {

            sourceElement.textContent =
                `Coupled Flood Nowcast — ${
                    forecast.time_label ??
                    `+${minutesAhead} min`
                }`;
        }


        const timeElement =
            document.getElementById(
                "model-time"
            );


        if (timeElement) {

            timeElement.textContent =
                data.generated_at
                    ? new Date(
                        data.generated_at
                    ).toLocaleString()
                    : "--";
        }


        setBackendStatus(
            true
        );


        console.log(
            "FLOOD RISK LAYER RENDERED:",
            floodCells.length
        );


        console.log(
            "DRAINAGE NETWORK RENDERED:",
            drainageStatuses
        );


        setTimeout(
            function () {

                map.invalidateSize();

            },
            100
        );
    }

    catch (error) {

        console.error(
            "SIH26085 Flood Nowcast Error:",
            error
        );


        setBackendStatus(
            false
        );
    }
}


/* ============================================================
   DRAINAGE STATUS TEXT
   ============================================================ */

function getDrainageStatusText(
    status
) {

    const normalized =
        String(
            status ||
            "unknown"
        )
            .toLowerCase()
            .trim();


    if (
        normalized ===
        "within_capacity"
    ) {

        return "WITHIN CAPACITY";
    }


    if (
        normalized ===
        "near_capacity"
    ) {

        return "NEAR CAPACITY";
    }


    if (
        normalized ===
        "over_capacity"
    ) {

        return "OVER CAPACITY";
    }


    if (
        normalized ===
        "severe_surcharge"
    ) {

        return "SEVERE SURCHARGE";
    }


    return "UNKNOWN";
}


/* ============================================================
   DRAINAGE COLOR
   ============================================================ */

function getDrainageColor(
    status
) {

    const normalized =
        String(
            status ||
            "unknown"
        )
            .toLowerCase()
            .trim();


    return (
        DRAINAGE_COLORS[
            normalized
        ] ||
        DRAINAGE_COLORS.unknown
    );
}


/* ============================================================
   DRAW DRAINAGE NETWORK
   ============================================================ */

function drawDrainageNetwork(
    drainageStatuses = {}
) {

    if (
        drainageNetworkLayer
    ) {

        map.removeLayer(
            drainageNetworkLayer
        );

        drainageNetworkLayer =
            null;
    }


    const layers =
        [];


    Object.entries(
        DRAINAGE_EDGES
    ).forEach(
        function (
            [edgeId, edge]
        ) {

            const status =
                drainageStatuses[
                    edgeId
                ] ||
                "unknown";


            const color =
                getDrainageColor(
                    status
                );


            const outerLine =
                L.polyline(
                    [
                        edge.from,
                        edge.to
                    ],
                    {

                        pane:
                            "drainageNetwork",

                        color:
                            "#0f172a",

                        weight:
                            20,

                        opacity:
                            0.85,

                        lineCap:
                            "round",

                        lineJoin:
                            "round",

                        interactive:
                            true
                    }
                );


            const line =
                L.polyline(
                    [
                        edge.from,
                        edge.to
                    ],
                    {

                        pane:
                            "drainageNetwork",

                        color:
                            color,

                        weight:
                            14,

                        opacity:
                            1,

                        lineCap:
                            "round",

                        lineJoin:
                            "round",

                        interactive:
                            true
                    }
                );


            line.bindPopup(
                `
                <div class="flood-popup">

                    <div class="popup-title">
                        Drainage ${edgeId}
                    </div>

                    <div class="popup-row">
                        <span>From</span>

                        <strong>
                            ${edge.fromNode}
                        </strong>
                    </div>

                    <div class="popup-row">
                        <span>To</span>

                        <strong>
                            ${edge.toNode}
                        </strong>
                    </div>

                    <div class="popup-row">
                        <span>Status</span>

                        <strong
                            style="color:${color};"
                        >
                            ${getDrainageStatusText(
                                status
                            )}
                        </strong>
                    </div>

                    <div class="popup-source">
                        Development synthetic
                        drainage network
                    </div>

                </div>
                `
            );


            line.bindTooltip(
                `
                    <strong>
                        ${edgeId}
                    </strong>
                    <br>
                    ${getDrainageStatusText(
                        status
                    )}
                `,
                {

                    direction:
                        "top",

                    sticky:
                        true
                }
            );


            line.on(
                "mouseover",
                function () {

                    this.setStyle({

                        weight:
                            18,

                        opacity:
                            1
                    });
                }
            );


            line.on(
                "mouseout",
                function () {

                    this.setStyle({

                        weight:
                            14,

                        opacity:
                            1
                    });
                }
            );


            layers.push(
                outerLine
            );

            layers.push(
                line
            );
        }
    );


    Object.entries(
        DRAINAGE_NODES
    ).forEach(
        function (
            [nodeId, coordinates]
        ) {

            const marker =
                L.circleMarker(
                    coordinates,
                    {

                        pane:
                            "drainageNetwork",

                        radius:
                            8,

                        fillColor:
                            "#ffffff",

                        fillOpacity:
                            1,

                        color:
                            "#2563eb",

                        weight:
                            3,

                        opacity:
                            1
                    }
                );


            marker.bindTooltip(
                `
                    <strong>
                        Drainage Node ${nodeId}
                    </strong>
                `,
                {

                    direction:
                        "top",

                    offset:
                        [0, -8]
                }
            );


            layers.push(
                marker
            );
        }
    );


    drainageNetworkLayer =
        L.layerGroup(
            layers
        );


    drainageNetworkLayer.addTo(
        map
    );


    console.log(
        "DRAINAGE NETWORK RENDERED:",
        drainageStatuses
    );
}


/* ============================================================
   LOAD SAFE ROUTE
   ============================================================ */

async function loadSafeRoute() {

    try {

        const forecastElement =
            document.getElementById(
                "forecast-time"
            );


        const minutesAhead =
            forecastElement
                ? Number(
                    forecastElement.value
                )
                : 0;


        const scenarioElement =
            document.getElementById(
                "scenario-select"
            );


        const scenario =
            scenarioElement
                ? scenarioElement.value
                : "heavy";


        console.log(
            "Loading safe route:",
            scenario,
            minutesAhead
        );


        const response =
            await fetch(
                `${API_URL}/flood/safe-route` +
                `?scenario=${encodeURIComponent(
                    scenario
                )}` +
                `&minutes_ahead=${minutesAhead}`,
                {
                    method:
                        "GET",

                    headers:
                        {
                            "Accept":
                                "application/json"
                        },

                    cache:
                        "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `Safe route API HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        if (
            !data ||
            data.status !== "success" ||
            !data.route
        ) {

            throw new Error(
                "Invalid safe route response"
            );
        }


        const route =
            data.route;


        console.log(
            "SAFE ROUTE API RESPONSE:",
            data
        );


        /* ====================================================
           UPDATE SIDEBAR
           ==================================================== */

        const routeStatus =
            document.getElementById(
                "route-status"
            );


        const routeRisk =
            normalizeRisk(
                route.route_status
            );


        if (routeStatus) {

            routeStatus.textContent =
                String(
                    route.route_status ||
                    "UNKNOWN"
                ).toUpperCase();


            routeStatus.style.color =
                routeRisk
                    ? getRiskColor(
                        routeRisk
                    )
                    : "#2563eb";
        }


        const startElement =
            document.getElementById(
                "route-start"
            );


        if (startElement) {

            startElement.textContent =
                route.start_node ||
                "N1";
        }


        const destinationElement =
            document.getElementById(
                "route-destination"
            );


        if (destinationElement) {

            destinationElement.textContent =
                route.destination_node ||
                "N4";
        }


        const distanceElement =
            document.getElementById(
                "route-distance"
            );


        if (distanceElement) {

            distanceElement.textContent =
                `${safeNumber(
                    route.route_distance_m
                ).toFixed(0)} m`;
        }


        const depthElement =
            document.getElementById(
                "route-depth"
            );


        if (depthElement) {

            depthElement.textContent =
                `${safeNumber(
                    route.max_water_depth_cm
                ).toFixed(2)} cm`;
        }


        const blockedElement =
            document.getElementById(
                "route-blocked"
            );


        if (blockedElement) {

            blockedElement.textContent =
                safeNumber(
                    route.blocked_segments
                );
        }


        const dangerousElement =
            document.getElementById(
                "route-dangerous"
            );


        if (dangerousElement) {

            dangerousElement.textContent =
                safeNumber(
                    route.dangerous_segments
                );
        }


        /* ====================================================
           REMOVE OLD SAFE ROUTE
           ==================================================== */

        if (safeRouteLayer) {

            map.removeLayer(
                safeRouteLayer
            );

            safeRouteLayer =
                null;
        }


        /* ====================================================
           READ ROUTE COORDINATES
           ==================================================== */

        const rawCoordinates =
            Array.isArray(
                route.route_coordinates
            )
                ? route.route_coordinates
                : [];


        const routeLatLngs =
            [];


        rawCoordinates.forEach(
            function (point) {

                if (
                    point &&
                    point.latitude !== undefined &&
                    point.longitude !== undefined
                ) {

                    routeLatLngs.push([
                        Number(
                            point.latitude
                        ),
                        Number(
                            point.longitude
                        )
                    ]);

                    return;
                }


                if (
                    point &&
                    point.lat !== undefined &&
                    point.lng !== undefined
                ) {

                    routeLatLngs.push([
                        Number(
                            point.lat
                        ),
                        Number(
                            point.lng
                        )
                    ]);

                    return;
                }


                if (
                    Array.isArray(point) &&
                    point.length >= 2
                ) {

                    routeLatLngs.push([
                        Number(
                            point[0]
                        ),
                        Number(
                            point[1]
                        )
                    ]);
                }
            }
        );


        if (
            routeLatLngs.length < 2
        ) {

            console.warn(
                "No valid safe route coordinates."
            );

            return;
        }


        /* ====================================================
           VISUAL OFFSET
           ==================================================== */

        /*
           Backend route coordinates are NOT modified.

           Only the frontend display is offset slightly
           because the development route and drainage
           network currently use identical synthetic geometry.
        */

        const ROUTE_VISUAL_OFFSET_LAT =
            0.00028;


        const ROUTE_VISUAL_OFFSET_LNG =
            0.00028;


        const visualRouteLatLngs =
            routeLatLngs.map(
                function (point) {

                    return [

                        point[0]
                            + ROUTE_VISUAL_OFFSET_LAT,

                        point[1]
                            + ROUTE_VISUAL_OFFSET_LNG

                    ];
                }
            );


        /* ====================================================
           SAFE ROUTE OUTER BORDER
           ==================================================== */

        const routeOuter =
            L.polyline(
                visualRouteLatLngs,
                {

                    pane:
                        "safeRoute",

                    color:
                        "#ffffff",

                    weight:
                        15,

                    opacity:
                        1,

                    lineCap:
                        "round",

                    lineJoin:
                        "round",

                    interactive:
                        false
                }
            );


        /* ====================================================
           SAFE ROUTE BLUE LINE
           ==================================================== */

        const routeInner =
            L.polyline(
                visualRouteLatLngs,
                {

                    pane:
                        "safeRoute",

                    color:
                        "#2563eb",

                    weight:
                        9,

                    opacity:
                        1,

                    dashArray:
                        "14,10",

                    lineCap:
                        "round",

                    lineJoin:
                        "round",

                    interactive:
                        true
                }
            );


        /* ====================================================
           START MARKER
           ==================================================== */

        const startMarker =
            L.circleMarker(
                visualRouteLatLngs[0],
                {

                    pane:
                        "safeRoute",

                    radius:
                        11,

                    fillColor:
                        "#22c55e",

                    fillOpacity:
                        1,

                    color:
                        "#ffffff",

                    weight:
                        4
                }
            );


        /* ====================================================
           DESTINATION MARKER
           ==================================================== */

        const endMarker =
            L.circleMarker(
                visualRouteLatLngs[
                    visualRouteLatLngs.length - 1
                ],
                {

                    pane:
                        "safeRoute",

                    radius:
                        11,

                    fillColor:
                        "#ef4444",

                    fillOpacity:
                        1,

                    color:
                        "#ffffff",

                    weight:
                        4
                }
            );


        /* ====================================================
           ROUTE POPUP
           ==================================================== */

        routeInner.bindPopup(
            `
            <div class="flood-popup">

                <div class="popup-title">
                    Flood-Safe Route
                </div>

                <div class="popup-row">
                    <span>Status</span>

                    <strong
                        style="color:${
                            routeRisk
                                ? getRiskColor(
                                    routeRisk
                                )
                                : "#2563eb"
                        };"
                    >
                        ${
                            String(
                                route.route_status ||
                                "UNKNOWN"
                            ).toUpperCase()
                        }
                    </strong>
                </div>

                <div class="popup-row">
                    <span>Distance</span>

                    <strong>
                        ${safeNumber(
                            route.route_distance_m
                        ).toFixed(0)} m
                    </strong>
                </div>

                <div class="popup-row">
                    <span>Maximum Depth</span>

                    <strong>
                        ${safeNumber(
                            route.max_water_depth_cm
                        ).toFixed(2)} cm
                    </strong>
                </div>

                <div class="popup-row">
                    <span>Blocked Segments</span>

                    <strong>
                        ${safeNumber(
                            route.blocked_segments
                        )}
                    </strong>
                </div>

                <div class="popup-source">
                    Development routing model
                </div>

            </div>
            `
        );


        startMarker.bindPopup(
            `
            <strong>
                Start:
                ${route.start_node || "N1"}
            </strong>
            `
        );


        endMarker.bindPopup(
            `
            <strong>
                Destination:
                ${route.destination_node || "N4"}
            </strong>
            `
        );


        safeRouteLayer =
            L.layerGroup([
                routeOuter,
                routeInner,
                startMarker,
                endMarker
            ]);


        safeRouteLayer.addTo(
            map
        );


        if (
            !window.__safeRouteInitialFit
        ) {

            const bounds =
                L.latLngBounds(
                    routeLatLngs
                );


            if (
                bounds.isValid()
            ) {

                map.fitBounds(
                    bounds,
                    {
                        padding:
                            [100, 100],

                        maxZoom:
                            15,

                        animate:
                            false
                    }
                );
            }


            window.__safeRouteInitialFit =
                true;
        }


        setTimeout(
            function () {

                map.invalidateSize();

                routeOuter.bringToFront();

                routeInner.bringToFront();

                startMarker.bringToFront();

                endMarker.bringToFront();

            },
            100
        );


        console.log(
            "SAFE ROUTE RENDERED:",
            visualRouteLatLngs
        );
    }

    catch (error) {

        console.error(
            "SAFE ROUTE ERROR:",
            error
        );


        const routeStatus =
            document.getElementById(
                "route-status"
            );


        if (routeStatus) {

            routeStatus.textContent =
                "ERROR";

            routeStatus.style.color =
                "#ef4444";
        }
    }
}


/* ============================================================
   BLOCKAGE SIMULATION
   ============================================================ */

async function simulateDrainageBlockage() {

    const edgeElement =
        document.getElementById(
            "blocked-edge-select"
        );


    if (!edgeElement) {

        console.warn(
            "Blocked drainage edge selector not found."
        );

        return;
    }


    const edgeId =
        edgeElement.value;


    const scenarioElement =
        document.getElementById(
            "scenario-select"
        );


    const scenario =
        scenarioElement
            ? scenarioElement.value
            : "heavy";


    const forecastElement =
        document.getElementById(
            "forecast-time"
        );


    const minutesAhead =
        forecastElement
            ? Number(
                forecastElement.value
            )
            : 60;


    const statusElement =
        document.getElementById(
            "blockage-status"
        );


    if (statusElement) {

        statusElement.textContent =
            "Simulating...";

        statusElement.style.color =
            "#eab308";
    }


    try {

        const response =
            await fetch(

                `${API_URL}/flood/blockage-simulation` +
                `?scenario=${encodeURIComponent(
                    scenario
                )}` +
                `&minutes_ahead=${minutesAhead}` +
                `&edge_id=${encodeURIComponent(
                    edgeId
                )}`,

                {

                    method:
                        "GET",

                    headers:
                        {
                            "Accept":
                                "application/json"
                        },

                    cache:
                        "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `Blockage API HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        console.log(
            "BLOCKAGE API RESPONSE:",
            data
        );


        if (
            !data ||
            data.status !== "success"
        ) {

            throw new Error(
                data?.message ||
                "Blockage simulation failed"
            );
        }


        const edges =
            Array.isArray(
                data.drainage_edges
            )
                ? data.drainage_edges
                : [];


        const selectedEdge =
            edges.find(
                function (edge) {

                    return (
                        edge.edge_id ===
                        edgeId
                    );
                }
            );


        if (!selectedEdge) {

            throw new Error(
                `Blocked edge ${edgeId} not found`
            );
        }


        /* ====================================================
           BLOCKAGE RESULT
           ==================================================== */

        const blockageResult =
            data.blockage_simulation ||
            data.simulation ||
            {};


        const originalCapacity =
            safeNumber(
                selectedEdge.original_capacity_m3s ??
                blockageResult.original_capacity_m3s ??
                selectedEdge.capacity_m3s
            );


        const simulatedCapacity =
            safeNumber(
                selectedEdge.simulated_capacity_m3s ??
                blockageResult.simulated_capacity_m3s
            );


        const utilization =
            safeNumber(
                selectedEdge.utilization
            )
            * 100;


        const reduction =
            originalCapacity > 0 &&
            simulatedCapacity >= 0
                ? Math.round(
                    (
                        1 -
                        (
                            simulatedCapacity /
                            originalCapacity
                        )
                    )
                    * 100
                )
                : safeNumber(
                    blockageResult.capacity_reduction_percent,
                    80
                );


        const impactedCells =
            safeNumber(
                blockageResult.impacted_flood_cells ??
                blockageResult.impacted_cells ??
                0
            );


        /*
           IMPORTANT:
           Backend returns:

               peak_original_water_depth_cm

           and:

               peak_simulated_water_depth_cm
        */

        const originalDepth =
            safeNumber(
                blockageResult.peak_original_water_depth_cm ??
                blockageResult.original_peak_depth_cm ??
                0
            );


        const simulatedDepth =
            safeNumber(
                blockageResult.peak_simulated_water_depth_cm ??
                blockageResult.simulated_peak_depth_cm ??
                0
            );


        /* ====================================================
           UPDATE UI
           ==================================================== */

        const blockedEdgeElement =
            document.getElementById(
                "blocked-edge"
            );


        if (blockedEdgeElement) {

            blockedEdgeElement.textContent =
                selectedEdge.edge_id;
        }


        const originalCapacityElement =
            document.getElementById(
                "original-capacity"
            );


        if (originalCapacityElement) {

            originalCapacityElement.textContent =
                `${originalCapacity.toFixed(
                    2
                )} m³/s`;
        }


        const simulatedCapacityElement =
            document.getElementById(
                "simulated-capacity"
            );


        if (simulatedCapacityElement) {

            simulatedCapacityElement.textContent =
                `${simulatedCapacity.toFixed(
                    2
                )} m³/s`;
        }


        const capacityReductionElement =
            document.getElementById(
                "capacity-reduction"
            );


        if (capacityReductionElement) {

            capacityReductionElement.textContent =
                `${reduction}%`;
        }


        const utilizationElement =
            document.getElementById(
                "blockage-utilization"
            );


        if (utilizationElement) {

            utilizationElement.textContent =
                `${utilization.toFixed(
                    2
                )}%`;
        }


        const edgeStatusElement =
            document.getElementById(
                "blockage-edge-status"
            );


        if (edgeStatusElement) {

            edgeStatusElement.textContent =
                String(
                    selectedEdge.status ||
                    "severe_surcharge"
                ).toUpperCase();


            edgeStatusElement.style.color =
                getDrainageColor(
                    selectedEdge.status
                );
        }


        const impactedCellsElement =
            document.getElementById(
                "blockage-impacted-cells"
            );


        if (impactedCellsElement) {

            impactedCellsElement.textContent =
                impactedCells;
        }


        const originalDepthElement =
            document.getElementById(
                "blockage-original-depth"
            );


        if (originalDepthElement) {

            originalDepthElement.textContent =
                `${originalDepth.toFixed(
                    2
                )} cm`;
        }


        const simulatedDepthElement =
            document.getElementById(
                "blockage-simulated-depth"
            );


        if (simulatedDepthElement) {

            simulatedDepthElement.textContent =
                `${simulatedDepth.toFixed(
                    2
                )} cm`;
        }


        if (statusElement) {

            statusElement.textContent =
                "Active";

            statusElement.style.color =
                "#22c55e";
        }


        /* ----------------------------------------------------
           HIGHLIGHT BLOCKED EDGE
           ---------------------------------------------------- */

        highlightBlockedDrainageEdge(
            edgeId,
            selectedEdge.status
        );


        console.log(
            "BLOCKAGE SIMULATION COMPLETE:",
            {

                edgeId:
                    edgeId,

                originalCapacity:
                    originalCapacity,

                simulatedCapacity:
                    simulatedCapacity,

                utilization:
                    utilization,

                reduction:
                    reduction,

                impactedCells:
                    impactedCells,

                originalDepth:
                    originalDepth,

                simulatedDepth:
                    simulatedDepth
            }
        );
    }

    catch (error) {

        console.error(
            "BLOCKAGE SIMULATION ERROR:",
            error
        );


        if (statusElement) {

            statusElement.textContent =
                "Error";

            statusElement.style.color =
                "#ef4444";
        }
    }
}


/* ============================================================
   HIGHLIGHT BLOCKED DRAINAGE EDGE
   ============================================================ */

function highlightBlockedDrainageEdge(
    edgeId,
    status = "severe_surcharge"
) {

    if (
        blockageLayer
    ) {

        map.removeLayer(
            blockageLayer
        );

        blockageLayer =
            null;
    }


    const edge =
        DRAINAGE_EDGES[
            edgeId
        ];


    if (!edge) {

        console.warn(
            "Blocked drainage edge not found:",
            edgeId
        );

        return;
    }


    const coordinates =
        [
            edge.from,
            edge.to
        ];


    const outerLine =
        L.polyline(
            coordinates,
            {

                pane:
                    "blockedDrainage",

                color:
                    "#111827",

                weight:
                    20,

                opacity:
                    0.95,

                lineCap:
                    "round",

                lineJoin:
                    "round",

                interactive:
                    true
            }
        );


    const blockageLine =
        L.polyline(
            coordinates,
            {

                pane:
                    "blockedDrainage",

                color:
                    "#ef4444",

                weight:
                    12,

                opacity:
                    1,

                dashArray:
                    "14,8",

                lineCap:
                    "round",

                lineJoin:
                    "round",

                interactive:
                    true
            }
        );


    blockageLayer =
        L.layerGroup(
            [
                outerLine,
                blockageLine
            ]
        );


    blockageLayer.addTo(
        map
    );


    blockageLine.bindPopup(
        `
        <div class="flood-popup">

            <div class="popup-title">
                Blocked Drainage
            </div>

            <div class="popup-row">
                <span>Edge</span>

                <strong>
                    ${edgeId}
                </strong>
            </div>

            <div class="popup-row">
                <span>Status</span>

                <strong
                    style="color:#ef4444;"
                >
                    BLOCKED
                </strong>
            </div>

            <div class="popup-row">
                <span>Model Status</span>

                <strong
                    style="color:#ef4444;"
                >
                    ${getDrainageStatusText(
                        status
                    )}
                </strong>
            </div>

            <div class="popup-source">
                Development blockage
                simulation
            </div>

        </div>
        `
    );


    blockageLine.bindTooltip(
        `
            <strong>
                BLOCKED ${edgeId}
            </strong>
        `,
        {

            direction:
                "top",

            sticky:
                true
        }
    );


    blockageLine.on(
        "mouseover",
        function () {

            this.setStyle({

                weight:
                    16,

                opacity:
                    1
            });
        }
    );


    blockageLine.on(
        "mouseout",
        function () {

            this.setStyle({

                weight:
                    12,

                opacity:
                    1
            });
        }
    );


    console.log(
        "BLOCKED DRAINAGE EDGE RENDERED:",
        edgeId
    );
}


/* ============================================================
   FORECAST SELECTOR
   ============================================================ */

function initializeForecastSelector() {

    const element =
        document.getElementById(
            "forecast-time"
        );


    if (!element) {

        console.warn(
            "Forecast selector not found."
        );

        return;
    }


    element.addEventListener(
        "change",
        async function () {

            console.log(
                "Forecast changed:",
                this.value
            );


            await loadFloodLayer();

            await loadSafeRoute();

            await loadFloodForecastChart();
        }
    );
}


/* ============================================================
   SCENARIO SELECTOR
   ============================================================ */

function initializeScenarioSelector() {

    const element =
        document.getElementById(
            "scenario-select"
        );


    if (!element) {

        console.warn(
            "Scenario selector not found."
        );

        return;
    }


    element.addEventListener(
        "change",
        async function () {

            console.log(
                "Scenario changed:",
                this.value
            );


            await loadFloodLayer();

            await loadSafeRoute();

            await loadFloodForecastChart();
        }
    );
}


/* ============================================================
   BLOCKAGE BUTTON
   ============================================================ */

function initializeBlockageSimulation() {

    const button =
        document.getElementById(
            "simulate-blockage-btn"
        );


    if (!button) {

        console.warn(
            "Blockage simulation button not found."
        );

        return;
    }


    button.addEventListener(
        "click",
        simulateDrainageBlockage
    );


    console.log(
        "Drainage blockage simulation initialized."
    );
}


/* ============================================================
   FORECAST CHART
   ============================================================ */

async function loadFloodForecastChart() {

    try {

        const scenarioElement =
            document.getElementById(
                "scenario-select"
            );


        const scenario =
            scenarioElement
                ? scenarioElement.value
                : "heavy";


        /* ====================================================
           SELECTED FORECAST TIME
           ==================================================== */

        const forecastElement =
            document.getElementById(
                "forecast-time"
            );


        const selectedMinutes =
            forecastElement
                ? Number(
                    forecastElement.value
                )
                : 0;


        /* ====================================================
           GET FULL 0–3 HOUR FORECAST
           ==================================================== */

        const response =
            await fetch(

                `${API_URL}/flood/nowcast` +
                `?scenario=${encodeURIComponent(
                    scenario
                )}`,

                {

                    method:
                        "GET",

                    headers:
                        {
                            "Accept":
                                "application/json"
                        },

                    cache:
                        "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `Forecast API HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        if (
            !data ||
            !Array.isArray(
                data.forecasts
            )
        ) {

            throw new Error(
                "Invalid forecast data"
            );
        }


        /* ====================================================
           CHART DATA
           ==================================================== */

        const labels =
            data.forecasts.map(
                function (forecast) {

                    return `+${
                        forecast.minutes_ahead
                    } min`;
                }
            );


        const rainfallData =
            data.forecasts.map(
                function (forecast) {

                    return safeNumber(
                        forecast.rainfall_mm
                    );
                }
            );


        const depthData =
            data.forecasts.map(
                function (forecast) {

                    return safeNumber(
                        forecast.max_water_depth_cm
                    );
                }
            );


        /* ====================================================
           FIND SELECTED FORECAST POINT
           ==================================================== */

        const selectedIndex =
            data.forecasts.findIndex(
                function (forecast) {

                    return (
                        Number(
                            forecast.minutes_ahead
                        ) === selectedMinutes
                    );
                }
            );


        /* ====================================================
           PEAK FORECAST
           ==================================================== */

        let peakForecast =
            null;


        let peakDepth =
            -1;


        data.forecasts.forEach(
            function (forecast) {

                const depth =
                    safeNumber(
                        forecast.max_water_depth_cm
                    );


                if (
                    depth >
                    peakDepth
                ) {

                    peakDepth =
                        depth;

                    peakForecast =
                        forecast;
                }
            }
        );


        if (peakForecast) {

            const peakTime =
                document.getElementById(
                    "peak-time"
                );


            if (peakTime) {

                peakTime.textContent =
                    `+${
                        peakForecast.minutes_ahead
                    } min`;
            }


            const peakRainfall =
                document.getElementById(
                    "peak-rainfall"
                );


            if (peakRainfall) {

                peakRainfall.textContent =
                    `${safeNumber(
                        peakForecast.rainfall_mm
                    ).toFixed(2)} mm`;
            }


            const peakDepthElement =
                document.getElementById(
                    "peak-depth"
                );


            if (peakDepthElement) {

                peakDepthElement.textContent =
                    `${peakDepth.toFixed(
                        2
                    )} cm`;
            }


            const peakRisk =
                document.getElementById(
                    "peak-risk"
                );


            if (peakRisk) {

                const risk =
    getRiskFromDepth(
        peakDepth
    );


                peakRisk.textContent =
                    risk.toUpperCase();


                peakRisk.style.color =
                    getRiskColor(
                        risk
                    );
            }
        }


        /* ====================================================
           CHART CANVAS
           ==================================================== */

        const canvas =
            document.getElementById(
                "flood-forecast-chart"
            );


        if (!canvas) {

            console.warn(
                "Forecast chart canvas not found."
            );

            return;
        }


        /* ====================================================
           DESTROY OLD CHART
           ==================================================== */

        if (
            floodForecastChart
        ) {

            floodForecastChart.destroy();

            floodForecastChart =
                null;
        }


        /* ====================================================
           CREATE CHART
           ==================================================== */

        floodForecastChart =
            new Chart(
                canvas,
                {

                    type:
                        "line",

                    data:
                        {

                            labels:
                                labels,

                            datasets:
                                [

                                    /* --------------------------------
                                       RAINFALL
                                       -------------------------------- */

                                    {

                                        label:
                                            "Rainfall (mm)",

                                        data:
                                            rainfallData,

                                        borderWidth:
                                            3,

                                        tension:
                                            0.3,

                                        pointRadius:
                                            rainfallData.map(
                                                function (_, index) {

                                                    return (
                                                        index ===
                                                        selectedIndex
                                                    )
                                                        ? 7
                                                        : 3;
                                                }
                                            ),

                                        pointHoverRadius:
                                            rainfallData.map(
                                                function (_, index) {

                                                    return (
                                                        index ===
                                                        selectedIndex
                                                    )
                                                        ? 9
                                                        : 5;
                                                }
                                            ),

                                        yAxisID:
                                            "rainfall"
                                    },


                                    /* --------------------------------
                                       WATER DEPTH
                                       -------------------------------- */

                                    {

                                        label:
                                            "Max Water Depth (cm)",

                                        data:
                                            depthData,

                                        borderWidth:
                                            3,

                                        tension:
                                            0.3,

                                        pointRadius:
                                            depthData.map(
                                                function (_, index) {

                                                    return (
                                                        index ===
                                                        selectedIndex
                                                    )
                                                        ? 7
                                                        : 3;
                                                }
                                            ),

                                        pointHoverRadius:
                                            depthData.map(
                                                function (_, index) {

                                                    return (
                                                        index ===
                                                        selectedIndex
                                                    )
                                                        ? 9
                                                        : 5;
                                                }
                                            ),

                                        yAxisID:
                                            "depth"
                                    }
                                ]
                        },

                    options:
                        {

                            responsive:
                                true,

                            maintainAspectRatio:
                                false,


                            interaction:
                                {

                                    mode:
                                        "index",

                                    intersect:
                                        false
                                },


                            plugins:
                                {

                                    legend:
                                        {

                                            display:
                                                true
                                        },


                                    title:
                                        {

                                            display:
                                                true,

                                            text:
                                                `Selected forecast: +${selectedMinutes} min`,

                                            padding:
                                                {
                                                    bottom:
                                                        8
                                                }
                                        }
                                },


                            scales:
                                {

                                    rainfall:
                                        {

                                            type:
                                                "linear",

                                            position:
                                                "left",

                                            title:
                                                {

                                                    display:
                                                        true,

                                                    text:
                                                        "Rainfall (mm)"
                                                }
                                        },


                                    depth:
                                        {

                                            type:
                                                "linear",

                                            position:
                                                "right",

                                            title:
                                                {

                                                    display:
                                                        true,

                                                    text:
                                                        "Water Depth (cm)"
                                                },

                                            grid:
                                                {

                                                    drawOnChartArea:
                                                        false
                                                }
                                        }
                                }
                        }
                }
            );


        console.log(
            "Flood forecast chart loaded:",
            scenario,
            "Selected:",
            selectedMinutes,
            "min"
        );
    }

    catch (error) {

        console.error(
            "FORECAST CHART ERROR:",
            error
        );
    }
}

/* ============================================================
   INTRO SCREEN
   ============================================================ */

function initializeIntro() {

    const intro =
        document.getElementById(
            "echelon-intro"
        );


    const enterButton =
        document.getElementById(
            "echelon-enter-btn"
        );


    if (
        !intro ||
        !enterButton
    ) {

        return;
    }


    enterButton.addEventListener(
        "click",
        function () {

            intro.classList.add(
                "hidden"
            );


            setTimeout(
                function () {

                    map.invalidateSize();

                },
                200
            );
        }
    );
}


/* ============================================================
   INITIAL DASHBOARD LOAD
   ============================================================ */

async function initializeDashboard() {

    console.log(
        "SIH26085 dashboard starting..."
    );


    createMapPanes();


    initializeForecastSelector();

    initializeScenarioSelector();

    initializeBlockageSimulation();

    initializeIntro();


    /* --------------------------------------------------------
       DRAW NETWORK FIRST
       -------------------------------------------------------- */

    drawDrainageNetwork(
        {}
    );


    /* --------------------------------------------------------
       LOAD DATA
       -------------------------------------------------------- */

    await loadFloodLayer();

    await loadSafeRoute();

    await loadFloodForecastChart();


    /* --------------------------------------------------------
       MAP SIZE
       -------------------------------------------------------- */

    setTimeout(
        function () {

            map.invalidateSize();

        },
        300
    );


    console.log(
        "SIH26085 dashboard ready."
    );
}


/* ============================================================
   AUTO REFRESH
   ============================================================ */

setInterval(
    async function () {

        try {

            console.log(
                "SIH26085 dashboard refresh"
            );


            await loadFloodLayer();

            await loadSafeRoute();

            await loadFloodForecastChart();

        }
        catch (error) {

            console.error(
                "AUTO REFRESH ERROR:",
                error
            );
        }

    },
    60000
);


/* ============================================================
   START APPLICATION
   ============================================================ */

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeDashboard
    );

}
else {

    initializeDashboard();
}


/* ============================================================
   DEBUG HELPERS
   ============================================================ */

window.SIH26085 =
    {

        map:
            map,

        reloadFlood:
            loadFloodLayer,

        reloadRoute:
            loadSafeRoute,

        reloadChart:
            loadFloodForecastChart,

        drawDrainage:
            drawDrainageNetwork,

        simulateBlockage:
            simulateDrainageBlockage,

        highlightBlocked:
            highlightBlockedDrainageEdge,

        layers:
            function () {

                return {

                    flood:
                        floodLayer,

                    drainage:
                        drainageNetworkLayer,

                    route:
                        safeRouteLayer,

                    blockage:
                        blockageLayer
                };
            },

        panes:
            function () {

                return {

                    floodPane:
                        map.getPane(
                            "floodMarkers"
                        ),

                    drainagePane:
                        map.getPane(
                            "drainageNetwork"
                        ),

                    routePane:
                        map.getPane(
                            "safeRoute"
                        ),

                    blockedPane:
                        map.getPane(
                            "blockedDrainage"
                        )
                };
            }
    };


console.log(
    "SIH26085 application JS loaded."
);