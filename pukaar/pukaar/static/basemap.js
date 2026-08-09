/*
 * Wayside basemap — Google-style light/dark cartography for the demo zone
 * and the wider city around it.
 *
 * Plain script (no ES module). Loaded via <script src="/static/basemap.js">.
 * Exposes window.WaysideBasemap.buildStyle(dataUrl, theme, zone, cityUrl),
 * which returns a complete MapLibre GL style reading from up to two GeoJSON
 * sources that share one schema:
 *
 *   "zone"  the pilot area (demo_zone.geojson) — real OpenStreetMap streets,
 *           and the SAME ones the router drives riders on
 *   "city"  the real arterials around it (demo_city.geojson) so that panning
 *           or zooming out shows Delhi instead of a void. Scenery only:
 *           nothing in it is routable.
 *
 * Both files are imported from OSM by tools/fetch_real_roads.py.
 * © OpenStreetMap contributors, ODbL — the attribution control on every map
 * carries the credit, and it must stay there.
 *
 * Schema for both:
 *   roads:     properties.kind === "road", properties.class in
 *              primary | secondary | residential | lane | footway,
 *              optional properties.name
 *   areas:     properties.kind in park | water | rail | campus | building.
 *              "rail" is a Polygon where OSM maps railway land use and a
 *              LineString for the tracks themselves — both are drawn
 *   landmarks: properties.kind === "landmark", properties.name,
 *              properties.icon in rail | monument | mosque | park |
 *              hospital | market
 *   places:    properties.kind === "place", properties.name,
 *              properties.rank 1 (district) or 2 (neighbourhood)
 *
 * Every road/area layer is generated once per source by terrainLayers(), so
 * the two render identically and the seam between them is invisible.
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
      railLine: "#b9b5ab",
      railTie: "#f2f0eb",
      building: "#e8e4dc",
      buildingOutline: "#dcd7cd",
      minorCasing: "#d5d3cc",
      minorFill: "#ffffff",
      majorCasing: "#f5cf70",
      majorFill: "#fce8a2",
      footway: "#b8b6ae",
      roadLabel: "#6b6b66",
      roadLabelHalo: "#ffffff",
      landmarkText: "#4a4a45",
      landmarkHalo: "#ffffff",
      landmarkDot: "#7a7a72",
      placeText: "#7c7a70",
      placeHoodText: "#8d8b80",
      // Light touch now that real streets are drawn outside: the mask marks
      // where Wayside operates without hiding the city around it.
      outsideMask: "rgba(120, 112, 96, 0.065)",
      frameLabel: "#8b8778",
      frameLabelHalo: "#f2f0eb"
    },
    night: {
      // Harmonizes with the app's dark UI (page background #0b0c10).
      land: "#14161c",
      campus: "#181b22",
      parkFill: "#17251c",
      parkOutline: "#213528",
      water: "#12283a",
      rail: "#1a1d24",
      railLine: "#3d4356",
      railTie: "#14161c",
      building: "#1c1f27",
      buildingOutline: "#242834",
      minorCasing: "#383e52",
      minorFill: "#2c3040",
      majorCasing: "#383e52",
      majorFill: "#3a3f55",
      footway: "#3a3e4c",
      roadLabel: "#8b8a82",
      roadLabelHalo: "#0b0c10",
      landmarkText: "#9a998f",
      landmarkHalo: "#0b0c10",
      landmarkDot: "#5c6270",
      placeText: "#8b91a0",
      placeHoodText: "#767c8b",
      outsideMask: "rgba(3, 4, 7, 0.30)",
      frameLabel: "#7c8291",
      frameLabelHalo: "#0b0c10"
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

  // A lat/lng circle as a coordinate ring (used for the pilot-zone frame).
  function circleRing(zone, radiusM, n) {
    var pts = [];
    var cosLat = Math.cos(zone.lat * Math.PI / 180);
    for (var i = 0; i <= n; i++) {
      var a = (i / n) * 2 * Math.PI;
      pts.push([
        zone.lng + (radiusM * Math.sin(a)) / (111320 * cosLat),
        zone.lat + (radiusM * Math.cos(a)) / 111320
      ]);
    }
    return pts;
  }

  // ---------------------------------------------------------------------
  // Terrain layers — the whole cartography for ONE source, generated so the
  // pilot zone and the surrounding city are drawn by identical rules and the
  // seam between them cannot show a style difference.
  // ---------------------------------------------------------------------
  function terrainLayers(src, t) {
    var sfx = src === "zone" ? "" : "-" + src;
    return [
      // ---- area fills ------------------------------------------------
      {
        id: "campus" + sfx,
        type: "fill",
        source: src,
        filter: kindIs("campus"),
        paint: { "fill-color": t.campus }
      },
      {
        id: "park" + sfx,
        type: "fill",
        source: src,
        filter: kindIs("park"),
        paint: { "fill-color": t.parkFill }
      },
      {
        id: "park-outline" + sfx,
        type: "line",
        source: src,
        filter: kindIs("park"),
        paint: {
          "line-color": t.parkOutline,
          "line-width": 0.8,
          "line-opacity": 0.9
        }
      },
      {
        id: "water" + sfx,
        type: "fill",
        source: src,
        filter: kindIs("water"),
        paint: { "fill-color": t.water }
      },
      {
        id: "rail" + sfx,
        type: "fill",
        source: src,
        filter: ["all", kindIs("rail"), ["==", ["geometry-type"], "Polygon"]],
        paint: { "fill-color": t.rail }
      },
      // Railways are LINEAR in OSM: a corridor polygon exists only where a
      // surveyor mapped the land use (yards, depots). The tracks themselves
      // are centrelines, drawn with the classic hatched casing — a solid
      // bed under a light dashed sleeper line — so Nizamuddin's junction
      // reads as a railway and not as a road a rider could be sent down.
      {
        id: "rail-bed" + sfx,
        type: "line",
        source: src,
        filter: ["all", kindIs("rail"), ["==", ["geometry-type"], "LineString"]],
        layout: { "line-cap": "butt" },
        paint: {
          "line-color": t.railLine,
          "line-width": [
            "interpolate", ["linear"], ["zoom"], 11, 1.2, 14, 2.4, 17, 4
          ],
          "line-opacity": 0.9
        }
      },
      {
        id: "rail-ties" + sfx,
        type: "line",
        source: src,
        minzoom: 13,
        filter: ["all", kindIs("rail"), ["==", ["geometry-type"], "LineString"]],
        paint: {
          "line-color": t.railTie,
          "line-width": [
            "interpolate", ["linear"], ["zoom"], 13, 0.8, 17, 2.2
          ],
          "line-dasharray": [2, 3],
          "line-opacity": 0.85
        }
      },

      // ---- building footprints (fade in from z14.2, Google-style) ----
      {
        id: "building" + sfx,
        type: "fill",
        source: src,
        minzoom: 14.2,
        filter: kindIs("building"),
        paint: {
          "fill-color": t.building,
          "fill-opacity": [
            "interpolate", ["linear"], ["zoom"],
            14.2, 0, 15, 0.75, 16.5, 1
          ],
          "fill-outline-color": t.buildingOutline
        }
      },

      // ---- footways (thin dashed, no casing) -------------------------
      {
        id: "road-footway" + sfx,
        type: "line",
        source: src,
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
        id: "road-minor-casing" + sfx,
        type: "line",
        source: src,
        // 12.4, not 13: at the far zoom the pilot zone is almost all minor
        // streets, and holding them back to 13 made it read as a clearing
        // punched in the surrounding city.
        minzoom: 12.4,
        filter: roadClassIn(["residential", "lane"]),
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": t.minorCasing,
          "line-width": minorWidth(1.6)
        }
      },
      {
        id: "road-minor" + sfx,
        type: "line",
        source: src,
        minzoom: 12.4,
        filter: roadClassIn(["residential", "lane"]),
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": t.minorFill,
          "line-width": minorWidth(0)
        }
      },
      {
        id: "road-major-casing" + sfx,
        type: "line",
        source: src,
        filter: roadClassIn(["primary", "secondary"]),
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": t.majorCasing,
          "line-width": majorWidth(1.6)
        }
      },
      {
        id: "road-major" + sfx,
        type: "line",
        source: src,
        filter: roadClassIn(["primary", "secondary"]),
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": t.majorFill,
          "line-width": majorWidth(0)
        }
      }
    ];
  }

  // Road-name labels for one source.
  function labelLayers(src, t) {
    var sfx = src === "zone" ? "" : "-" + src;
    return [
      {
        id: "road-label" + sfx,
        type: "symbol",
        source: src,
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
        id: "road-label-lane" + sfx,
        type: "symbol",
        source: src,
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
      }
    ];
  }

  // ---------------------------------------------------------------------
  // Style builder
  // ---------------------------------------------------------------------
  // zone ({lat, lng, radius_m}, optional): frames the pilot zone — marks
  // where Wayside actually operates, so the surrounding city reads as
  // context rather than as coverage.
  // cityUrl (optional): the wider surroundings; omit for the zone alone.
  function buildStyle(dataUrl, theme, zone, cityUrl) {
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
      }
    ];

    // City underneath, pilot zone on top: where they touch, the hand-built
    // geometry wins.
    if (cityUrl) layers = layers.concat(terrainLayers("city", t));
    layers = layers.concat(terrainLayers("zone", t));

    layers = layers.concat([
      // ---- pilot-zone frame (only when a zone is provided) -----------
      // inserted here so outside geometry dims but labels stay crisp
      {
        id: "zone-outside",
        type: "fill",
        source: "frame",
        filter: kindIs("outside"),
        paint: { "fill-color": t.outsideMask }
      },
      {
        id: "zone-frame-label",
        type: "symbol",
        source: "frame",
        filter: kindIs("edge"),
        layout: {
          "symbol-placement": "line",
          "symbol-spacing": 420,
          "text-field": "WAYSIDE PILOT ZONE",
          "text-font": FONT_STACK,
          "text-size": [
            "interpolate", ["linear"], ["zoom"],
            13, 10.5,
            16, 12.5
          ],
          "text-letter-spacing": 0.25
        },
        paint: {
          "text-color": t.frameLabel,
          "text-halo-color": t.frameLabelHalo,
          "text-halo-width": 1.2
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
      }
    ]);

    // ---- district / neighbourhood names in the wider city -------------
    // These are what make a zoomed-out view read as a city rather than as a
    // diagram: rank 1 districts hold from the furthest zoom, rank 2
    // neighbourhoods join once the streets under them are legible.
    if (cityUrl) {
      layers.push({
        id: "place-district",
        type: "symbol",
        source: "city",
        filter: ["all", kindIs("place"), ["==", ["get", "rank"], 1]],
        layout: {
          "text-field": ["get", "name"],
          "text-font": FONT_STACK,
          "text-size": [
            "interpolate", ["linear"], ["zoom"],
            11, 11, 13, 13, 15.5, 15
          ],
          "text-letter-spacing": 0.14,
          "text-transform": "uppercase",
          "text-max-width": 9,
          "text-padding": 6
        },
        paint: {
          "text-color": t.placeText,
          "text-halo-color": t.landmarkHalo,
          "text-halo-width": 1.4
        }
      });
      layers.push({
        id: "place-hood",
        type: "symbol",
        source: "city",
        minzoom: 12.6,
        filter: ["all", kindIs("place"), ["!=", ["get", "rank"], 1]],
        layout: {
          "text-field": ["get", "name"],
          "text-font": FONT_STACK,
          "text-size": [
            "interpolate", ["linear"], ["zoom"],
            12.6, 10.5, 15, 12.5
          ],
          "text-letter-spacing": 0.04,
          "text-max-width": 9,
          "text-padding": 4
        },
        paint: {
          "text-color": t.placeHoodText,
          "text-halo-color": t.landmarkHalo,
          "text-halo-width": 1.3
        }
      });
      layers = layers.concat(labelLayers("city", t));
    }
    layers = layers.concat(labelLayers("zone", t));

    layers.push({
      // ---- landmark labels -------------------------------------------
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
    });

    var sources = { zone: { type: "geojson", data: dataUrl } };
    if (cityUrl) sources.city = { type: "geojson", data: cityUrl };
    if (zone && zone.radius_m) {
      // world rectangle with a hole punched at ~1.12x the zone radius: the
      // dashed ring the pages draw sits just inside the dimmed edge
      var hole = circleRing(zone, zone.radius_m * 1.12, 96);
      sources.frame = {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              properties: { kind: "outside" },
              geometry: {
                type: "Polygon",
                coordinates: [
                  [[-179.9, -85], [179.9, -85], [179.9, 85],
                   [-179.9, 85], [-179.9, -85]],
                  hole
                ]
              }
            },
            {
              type: "Feature",
              properties: { kind: "edge" },
              geometry: { type: "LineString", coordinates: hole }
            }
          ]
        }
      };
    } else {
      layers = layers.filter(function (l) { return l.source !== "frame"; });
    }

    return {
      version: 8,
      name: "Wayside " + (theme === "night" ? "Night" : "Day"),
      metadata: { "wayside:theme": theme === "night" ? "night" : "day" },
      glyphs: glyphs,
      sources: sources,
      layers: layers
    };
  }

  window.WaysideBasemap = {
    buildStyle: buildStyle,
    THEMES: THEMES
  };
})();
