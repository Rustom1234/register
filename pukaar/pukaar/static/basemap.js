/*
 * Wayside basemap — Google-style light/dark cartography for the demo zone.
 *
 * Plain script (no ES module). Loaded via <script src="/static/basemap.js">.
 * Exposes window.WaysideBasemap.buildStyle(dataUrl, theme) which returns a
 * complete MapLibre GL style object reading every layer from a single
 * GeoJSON source ("zone") that follows the demo_zone.geojson schema:
 *
 *   roads:     properties.kind === "road", properties.class in
 *              primary | secondary | residential | lane | footway,
 *              optional properties.name
 *   areas:     properties.kind in park | water | rail | campus
 *   landmarks: properties.kind === "landmark", properties.name,
 *              properties.icon in rail | monument | mosque | park |
 *              hospital | market
 *
 * Glyph PBFs are vendored under /static/vendor/glyphs/Noto Sans Regular/
 * so no external requests are ever made at runtime.
 */
(function () {
  "use strict";

  // ---------------------------------------------------------------------
  // Theme palettes
  // ---------------------------------------------------------------------
  var THEMES = {
    day: {
      land: "#f2f0eb",
      campus: "#f0ebe1",
      parkFill: "#c5e8c2",
      parkOutline: "#a9d2a6",
      water: "#a6d8f5",
      rail: "#e4e2dd",
      minorCasing: "#d5d3cc",
      minorFill: "#ffffff",
      majorCasing: "#f5cf70",
      majorFill: "#fce8a2",
      footway: "#b8b6ae",
      roadLabel: "#6b6b66",
      roadLabelHalo: "#ffffff",
      landmarkText: "#4a4a45",
      landmarkHalo: "#ffffff",
      landmarkDot: "#7a7a72"
    },
    night: {
      // Harmonizes with the app's dark UI (page background #0b0c10).
      land: "#14161c",
      campus: "#181b22",
      parkFill: "#17251c",
      parkOutline: "#213528",
      water: "#12283a",
      rail: "#1a1d24",
      minorCasing: "#383e52",
      minorFill: "#2c3040",
      majorCasing: "#383e52",
      majorFill: "#3a3f55",
      footway: "#3a3e4c",
      roadLabel: "#8b8a82",
      roadLabelHalo: "#0b0c10",
      landmarkText: "#9a998f",
      landmarkHalo: "#0b0c10",
      landmarkDot: "#5c6270"
    }
  };

  var FONT_STACK = ["Noto Sans Regular"];

  // ---------------------------------------------------------------------
  // Filter helpers (all layers read from the single "zone" source)
  // ---------------------------------------------------------------------
  function kindIs(kind) {
    return ["==", ["get", "kind"], kind];
  }

  function roadClassIn(classes) {
    return [
      "all",
      ["==", ["get", "kind"], "road"],
      ["match", ["get", "class"], classes, true, false]
    ];
  }

  // Width interpolation helpers. Base fill widths per class, with the
  // casing drawn 1.6px wider underneath. Tuned to look clean at z14-z16.
  //   primary   1.2px @z12 -> 9px @z17
  //   secondary 1.0px @z12 -> 7px @z17
  //   residential 0.7px @z13 -> 5.5px @z17
  //   lane      0.4px @z13 -> 4px @z17
  //   footway   0.4px @z13 -> 1.8px @z17 (dashed, no casing)
  function majorWidth(extra) {
    return [
      "interpolate", ["linear"], ["zoom"],
      12, ["match", ["get", "class"], "primary", 1.2 + extra, 1.0 + extra],
      14, ["match", ["get", "class"], "primary", 3.2 + extra, 2.6 + extra],
      15, ["match", ["get", "class"], "primary", 5.0 + extra, 4.0 + extra],
      17, ["match", ["get", "class"], "primary", 9.0 + extra, 7.0 + extra]
    ];
  }

  function minorWidth(extra) {
    return [
      "interpolate", ["linear"], ["zoom"],
      13, ["match", ["get", "class"], "residential", 0.7 + extra, 0.4 + extra],
      14, ["match", ["get", "class"], "residential", 1.6 + extra, 1.0 + extra],
      15, ["match", ["get", "class"], "residential", 2.8 + extra, 1.8 + extra],
      17, ["match", ["get", "class"], "residential", 5.5 + extra, 4.0 + extra]
    ];
  }

  function footwayWidth() {
    return [
      "interpolate", ["linear"], ["zoom"],
      13, 0.4,
      15, 0.9,
      17, 1.8
    ];
  }

  // ---------------------------------------------------------------------
  // Style builder
  // ---------------------------------------------------------------------
  function buildStyle(dataUrl, theme) {
    var t = THEMES[theme === "night" ? "night" : "day"];

    // Same-origin only: glyphs are served from this app's own statics.
    var origin = typeof location !== "undefined" && location.origin &&
      location.origin !== "null" ? location.origin : "";
    var glyphs = origin + "/static/vendor/glyphs/{fontstack}/{range}.pbf";

    var layers = [
      // ---- land ------------------------------------------------------
      {
        id: "land",
        type: "background",
        paint: { "background-color": t.land }
      },

      // ---- area fills ------------------------------------------------
      {
        id: "campus",
        type: "fill",
        source: "zone",
        filter: kindIs("campus"),
        paint: { "fill-color": t.campus }
      },
      {
        id: "park",
        type: "fill",
        source: "zone",
        filter: kindIs("park"),
        paint: { "fill-color": t.parkFill }
      },
      {
        id: "park-outline",
        type: "line",
        source: "zone",
        filter: kindIs("park"),
        paint: {
          "line-color": t.parkOutline,
          "line-width": 0.8,
          "line-opacity": 0.9
        }
      },
      {
        id: "water",
        type: "fill",
        source: "zone",
        filter: kindIs("water"),
        paint: { "fill-color": t.water }
      },
      {
        id: "rail",
        type: "fill",
        source: "zone",
        filter: kindIs("rail"),
        paint: { "fill-color": t.rail }
      },

      // ---- footways (thin dashed, no casing) -------------------------
      {
        id: "road-footway",
        type: "line",
        source: "zone",
        minzoom: 13,
        filter: roadClassIn(["footway"]),
        layout: { "line-join": "round", "line-cap": "butt" },
        paint: {
          "line-color": t.footway,
          "line-width": footwayWidth(),
          "line-dasharray": [2, 2]
        }
      },

      // ---- casings under fills (minor first, majors above) -----------
      {
        id: "road-minor-casing",
        type: "line",
        source: "zone",
        minzoom: 13,
        filter: roadClassIn(["residential", "lane"]),
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": t.minorCasing,
          "line-width": minorWidth(1.6)
        }
      },
      {
        id: "road-minor",
        type: "line",
        source: "zone",
        minzoom: 13,
        filter: roadClassIn(["residential", "lane"]),
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": t.minorFill,
          "line-width": minorWidth(0)
        }
      },
      {
        id: "road-major-casing",
        type: "line",
        source: "zone",
        filter: roadClassIn(["primary", "secondary"]),
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": t.majorCasing,
          "line-width": majorWidth(1.6)
        }
      },
      {
        id: "road-major",
        type: "line",
        source: "zone",
        filter: roadClassIn(["primary", "secondary"]),
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": t.majorFill,
          "line-width": majorWidth(0)
        }
      },

      // ---- landmarks: dot under the label ----------------------------
      {
        id: "landmark-dot",
        type: "circle",
        source: "zone",
        minzoom: 13,
        filter: kindIs("landmark"),
        paint: {
          "circle-radius": 3,
          "circle-color": t.landmarkDot,
          "circle-stroke-width": 1,
          "circle-stroke-color": t.landmarkHalo
        }
      },

      // ---- road name labels (along the line) -------------------------
      {
        id: "road-label",
        type: "symbol",
        source: "zone",
        minzoom: 14,
        filter: [
          "all",
          roadClassIn(["primary", "secondary", "residential"]),
          ["has", "name"]
        ],
        layout: {
          "symbol-placement": "line",
          "text-field": ["get", "name"],
          "text-font": FONT_STACK,
          "text-size": [
            "interpolate", ["linear"], ["zoom"],
            14, 11,
            16, 12
          ],
          "text-letter-spacing": 0.02,
          "text-max-angle": 30
        },
        paint: {
          "text-color": t.roadLabel,
          "text-halo-color": t.roadLabelHalo,
          "text-halo-width": 1.2
        }
      },
      {
        id: "road-label-lane",
        type: "symbol",
        source: "zone",
        minzoom: 16,
        filter: [
          "all",
          roadClassIn(["lane", "footway"]),
          ["has", "name"]
        ],
        layout: {
          "symbol-placement": "line",
          "text-field": ["get", "name"],
          "text-font": FONT_STACK,
          "text-size": 11,
          "text-letter-spacing": 0.02,
          "text-max-angle": 30
        },
        paint: {
          "text-color": t.roadLabel,
          "text-halo-color": t.roadLabelHalo,
          "text-halo-width": 1.2
        }
      },

      // ---- landmark labels -------------------------------------------
      {
        id: "landmark-label",
        type: "symbol",
        source: "zone",
        minzoom: 13,
        filter: ["all", kindIs("landmark"), ["has", "name"]],
        layout: {
          "text-field": ["get", "name"],
          "text-font": FONT_STACK,
          "text-size": 12,
          "text-anchor": "top",
          "text-offset": [0, 0.5],
          "text-max-width": 8
        },
        paint: {
          "text-color": t.landmarkText,
          "text-halo-color": t.landmarkHalo,
          "text-halo-width": 1.2
        }
      }
    ];

    return {
      version: 8,
      name: "Wayside " + (theme === "night" ? "Night" : "Day"),
      metadata: { "wayside:theme": theme === "night" ? "night" : "day" },
      glyphs: glyphs,
      sources: {
        zone: { type: "geojson", data: dataUrl }
      },
      layers: layers
    };
  }

  window.WaysideBasemap = {
    buildStyle: buildStyle,
    THEMES: THEMES
  };
})();
