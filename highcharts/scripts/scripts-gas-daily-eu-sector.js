jQuery(document).ready(function () {
    (function waitHighcharts(ready) {
        if (typeof Highcharts !== "undefined") return ready();
        window.addEventListener("highcharts:ready", ready, { once: true });
    })(function () {
        let pymChild;
        let chart;
        let payloadRef = null;

        const COUNTRY_LABELS = {
            AT: "Austria",
            BE: "Belgium",
            BG: "Bulgaria",
            CZ: "Czech Republic",
            DE: "Germany",
            DK: "Denmark",
            EE: "Estonia",
            ES: "Spain",
            EU: "European Union",
            FI: "Finland",
            FR: "France",
            GR: "Greece",
            HR: "Croatia",
            HU: "Hungary",
            IT: "Italy",
            LT: "Lithuania",
            LU: "Luxembourg",
            LV: "Latvia",
            NL: "Netherlands",
            PL: "Poland",
            PT: "Portugal",
            RO: "Romania",
            SE: "Sweden",
            SI: "Slovenia",
            SK: "Slovakia",
            UK: "United Kingdom",
        };

        function initializePym() {
            pymChild = new pym.Child({ polling: 100, debug: false });
            const updateSize = () => {
                const w = Math.min(window.innerWidth, 1200);
                const h = Math.max(window.innerHeight * 0.8, 620);
                jQuery("#main-container").css({ width: `${w}px` });
                pymChild.sendHeight(h);
            };
            setTimeout(updateSize, 400);
            window.addEventListener("resize", updateSize);
        }

        function entityLabel(code) {
            if (code === "EU") return "European Union";
            return COUNTRY_LABELS[code] ? `${code} — ${COUNTRY_LABELS[code]}` : code;
        }

        function subtitleSubject(code) {
            if (code === "EU") return "EU aggregate by sector";
            return `${entityLabel(code)} by sector`;
        }

        function buildSubtitle(meta, code) {
            return `${subtitleSubject(code)}, ${meta.rolling_days}-day rolling average from Jan 2019 to ${meta.latest_date}`;
        }

        function orderedSeries(entityData, seriesOrder) {
            const byKey = {};
            (entityData.series || []).forEach((entry) => {
                byKey[entry.key] = entry;
            });
            return seriesOrder
                .filter((key) => byKey[key])
                .map((key) => byKey[key]);
        }

        function renderChart(selectedCode) {
            const meta = payloadRef.meta || {};
            const entityData = payloadRef.entities?.[selectedCode] || { series: [] };
            const series = orderedSeries(entityData, meta.series_order || []).map((entry) => ({
                type: "line",
                name: entry.name,
                data: entry.data,
                color: entry.color,
                marker: { enabled: false },
                lineWidth: entry.key === "total" ? 3 : 2,
                tooltip: {
                    valueSuffix: " TWh",
                },
            }));

            const titleText =
                selectedCode === "EU"
                    ? "EU natural gas demand by sector"
                    : `${entityLabel(selectedCode)} natural gas demand by sector`;
            const subtitleText = buildSubtitle(meta, selectedCode);

            if (!chart) {
                chart = Highcharts.stockChart("chart-container", {
                    rangeSelector: {
                        selected: 3,
                        buttons: [
                            { type: "year", count: 1, text: "1y" },
                            { type: "year", count: 3, text: "3y" },
                            { type: "year", count: 5, text: "5y" },
                            { type: "all", text: "All" },
                        ],
                    },
                    navigator: {
                        enabled: true,
                    },
                    scrollbar: {
                        enabled: false,
                    },
                    chart: {
                        spacingTop: 20,
                    },
                    title: {
                        text: titleText,
                        align: "left",
                        style: { fontWeight: "bold", fontSize: "20px" },
                    },
                    subtitle: {
                        text: subtitleText,
                        align: "left",
                        style: { color: "#666", fontSize: "13px" },
                    },
                    legend: {
                        enabled: true,
                        align: "center",
                        verticalAlign: "top",
                        layout: "horizontal",
                    },
                    xAxis: {
                        type: "datetime",
                    },
                    yAxis: {
                        title: { text: "TWh" },
                        min: 0,
                    },
                    tooltip: {
                        shared: true,
                        xDateFormat: "%e %b %Y",
                        valueDecimals: 2,
                        valueSuffix: " TWh",
                    },
                    plotOptions: {
                        series: {
                            dataGrouping: {
                                enabled: false,
                            },
                        },
                    },
                    exporting: {
                        enabled: true,
                        buttons: {
                            contextButton: {
                                menuItems: [
                                    "viewFullscreen",
                                    "printChart",
                                    "downloadPNG",
                                    "downloadCSV",
                                ],
                            },
                        },
                    },
                    credits: {
                        enabled: false,
                    },
                    series,
                });
            } else {
                while (chart.series.length > 0) {
                    chart.series[0].remove(false);
                }
                series.forEach((entry) => chart.addSeries(entry, false));
                chart.setTitle({ text: titleText }, { text: subtitleText });
                chart.redraw();
            }
        }

        function populateSelector(payload) {
            const select = jQuery("#country-select");
            const codes = Object.keys(payload.entities || {}).sort((a, b) => {
                if (a === "EU") return -1;
                if (b === "EU") return 1;
                return entityLabel(a).localeCompare(entityLabel(b));
            });

            select.empty();
            codes.forEach((code) => {
                select.append(
                    jQuery("<option/>", {
                        value: code,
                        text: entityLabel(code),
                    })
                );
            });
            select.val("EU");
            select.on("change", function () {
                renderChart(jQuery(this).val());
            });
        }

        jQuery.getJSON("data/eu_daily_sector_rolling30.json")
            .done(function (payload) {
                payloadRef = payload;
                populateSelector(payload);
                renderChart("EU");
                initializePym();
            })
            .fail(function () {
                jQuery("#chart-container").html(
                    "<p style='padding:1em;font-family:sans-serif'>Could not load data/eu_daily_sector_rolling30.json. Run: python3 -m src.exporters.eu_daily_sector_rolling_highcharts</p>"
                );
            });
    });
});
