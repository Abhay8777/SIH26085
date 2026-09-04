# SIH26085 — Urban Flood Nowcasting System

## 🌧️ Urban Flood Nowcasting System — Drainage and Rainfall Coupling

A web-based urban flood nowcasting prototype that combines rainfall scenarios, terrain elevation, surface runoff, drainage capacity, and drainage blockage effects to estimate short-term flood risk.

The system is designed for **0–3 hour urban flood nowcasting** and visualizes the results through an interactive GIS dashboard.

> **Current status:** Working prototype using development/simulated rainfall, DEM, and drainage data. The architecture is designed to accept official IMD rainfall data and real municipal geospatial datasets when access is available.

---

## 🎯 Problem Statement

Urban flooding cannot be predicted accurately using rainfall intensity alone.

Flood risk depends on multiple interacting factors:

- Rainfall intensity and spatial distribution
- Terrain elevation
- Surface runoff
- Drainage network capacity
- Drainage overload
- Drainage blockage
- Water accumulation

The objective of this project is to combine these factors and provide short-term, high-resolution flood-risk information for the next **0–3 hours**.

The system estimates:

- Potential flood-prone areas
- Water depth in centimeters
- Drainage overload
- Drainage blockage impact
- Flood severity
- Flood-aware route safety

---

## 💡 Proposed Solution

The system follows a:

**Rainfall → Runoff → Terrain → Drainage → Flood Risk**

pipeline.

```text
Rainfall / Nowcast
        ↓
Rainfall Grid
        ↓
DEM / Terrain
        ↓
Surface Runoff & Water Depth
        ↓
Drainage Network
        ↓
Drainage Capacity Analysis
        ↓
Flood Risk + Water Depth
        ↓
GIS Dashboard
        ↓
Safe Route / Blockage Analysis
