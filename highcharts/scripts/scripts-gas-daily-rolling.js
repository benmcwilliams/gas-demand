jQuery(document).ready(function () {
    const CATEGORY_ORDER = ["total", "power", "household", "industry"];

    const COUNTRY_LABELS = {
        AT: "Austria",
        BE: "Belgium",
        BG: "Bulgaria",
        HR: "Croatia",
        CY: "Cyprus",
        CZ: "Czech Republic",
        DK: "Denmark",
        EE: "Estonia",
        FI: "Finland",
        FR: "France",
        DE: "Germany",
        GR: "Greece",
        HU: "Hungary",
        IE: "Ireland",
        IT: "Italy",
        LV: "Latvia",
        LT: "Lithuania",
        LU: "Luxembourg",
        NL: "Netherlands",
        PL: "Poland",
        PT: "Portugal",
        RO: "Romania",
        SK: "Slovakia",
        SI: "Slovenia",
        ES: "Spain",
        SE: "Sweden",
        UK: "United Kingdom",
    };

    let pymChild;
    let chart;
    let fullPayload = null;

    function countryLabel(code) {
        const name = COUNTRY_LABELS[code];
        return name ? `${code} — ${name}` : code;
    }

    function initializePym() {
        pymChild = new pym.Child({ polling: 100, debug: false });
        const updateSize = () => {
            const w = Math.min(window.innerWidth, 1200);
            const h = Math.max(window.innerHeight * 0.85, 620);
            jQuery("#main-container").css({ width: `${w}px` });
            pymChild.sendHeight(h);
        };
        setTimeout(updateSize, 400);
        window.addEventListener("resize", updateSize);
    }

    /**
     * @param {string[]} codes
     * @param {string} typeKey
     * @param {"y2026"|"avg2019_2021"|"avg2022_2025"} seriesKey
     * @returns {[number, number|null][]}
     */
    function sumSeries(codes, typeKey, seriesKey) {
        const bucket = fullPayload.data[typeKey];
        if (!bucket) return [];

        const arrays = codes
            .map((c) => bucket[c]?.series?.[seriesKey])
            .filter((a) => a && a.length);

        if (!arrays.length) return [];

        const n = arrays[0].length;
        const out = [];
        for (let i = 0; i < n; i++) {
            const ms = arrays[0][i][0];
            let sum = 0;
            let any = false;
            for (const arr of arrays) {
                const y = arr[i][1];
                if (y !== null && y !== undefined && !Number.isNaN(y)) {
                    sum += y;
                    any = true;
                }
            }
            out.push([ms, any ? sum : null]);
        }
        return out;
    }

    function getSelectedCountries() {
        const selected = [];
        jQuery("#country-checkboxes input.country-cb:checked").each(function () {
            selected.push(jQuery(this).val());
        });
        return selected;
    }

    function rebuildCountryCheckboxes(typeKey) {
        const box = jQuery("#country-checkboxes");
        box.empty();
        const list = fullPayload.countriesByType[typeKey] || [];
        list.forEach((code) => {
            const id = `cb-${typeKey}-${code}`;
            const row = jQuery("<label/>", { class: "country-row", for: id });
            row.append(
                jQuery("<input/>", {
                    type: "checkbox",
                    class: "country-cb",
                    id,
                    value: code,
                    checked: true,
                })
            );
            row.append(jQuery("<span/>").text(countryLabel(code)));
            box.append(row);
        });
    }

    function buildChartSeries() {
        const typeKey = jQuery("#category-select").val();
        const codes = getSelectedCountries();
        const meta = fullPayload.meta;
        const yLabel = String(meta.plot_year);

        if (!codes.length) {
            return {
                series: [],
                subtitle: "Select at least one country",
            };
        }

        const s2026 = sumSeries(codes, typeKey, "y2026");
        const s1921 = sumSeries(codes, typeKey, "avg2019_2021");
        const s2225 = sumSeries(codes, typeKey, "avg2022_2025");

        const series = [
            {
                type: "line",
                name: yLabel,
                data: s2026,
                color: "#880E4F",
                dashStyle: "Solid",
                marker: { enabled: false },
                connectNulls: false,
            },
            {
                type: "line",
                name: "2019–2021 avg",
                data: s1921,
                color: "#757575",
                dashStyle: "ShortDash",
                marker: { enabled: false },
                connectNulls: false,
            },
            {
                type: "line",
                name: "2022–2025 avg",
                data: s2225,
                color: "#1565C0",
                dashStyle: "ShortDash",
                marker: { enabled: false },
                connectNulls: false,
            },
        ];

        const thru = fullPayload.meta?.y2026_included_through;
        const lag = fullPayload.meta?.y2026_recent_lag_days ?? 2;
        let subtitle = `${codes.length} countries — ${typeKey} (30-day trailing mean, TWh)`;
        if (thru) {
            subtitle += `. ${yLabel} through ${thru} (${lag}-day lag)`;
        }
        return { series, subtitle };
    }

    function updateChart() {
        const { series, subtitle } = buildChartSeries();

        const titleText = "Daily natural gas demand (30-day rolling average)";

        if (!chart) {
            chart = Highcharts.chart("chart-container", {
                chart: { type: "line", zoomType: "x" },
                title: {
                  text: titleText,
                  align: "left",
                  style: { fontWeight: "bold", fontSize: "18px" },
                },
                subtitle: {
                  text: subtitle,
                  align: "left",
                  style: { color: "#666", fontSize: "13px" },
                },
                legend: {
                  align: "center",
                  verticalAlign: "top",
                  layout: "horizontal",
                },
                xAxis: {
                  type: "datetime",
                  title: { text: null },
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
                  line: { marker: { enabled: false } },
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
                series,
            });
        } else {
            while (chart.series.length > 0) {
                chart.series[0].remove(false);
            }
            series.forEach((s) => chart.addSeries(s, false));
            chart.setTitle(null, { text: subtitle });
            chart.redraw();
        }
    }

    jQuery.getJSON("data/daily_demand_rolling30.json")
        .done(function (payload) {
            fullPayload = payload;
            rebuildCountryCheckboxes(jQuery("#category-select").val());
            updateChart();
        })
        .fail(function () {
            jQuery("#chart-container").html(
                "<p style='padding:1em;font-family:sans-serif'>Could not load data/daily_demand_rolling30.json. Run: python3 -m src.exporters.daily_rolling_highcharts</p>"
            );
        });

    jQuery("#category-select").on("change", function () {
        const v = jQuery(this).val();
        if (CATEGORY_ORDER.indexOf(v) < 0) return;
        rebuildCountryCheckboxes(v);
        updateChart();
    });

    jQuery("#country-checkboxes").on("change", "input.country-cb", updateChart);

    jQuery("#select-all-countries").on("click", function () {
        jQuery("#country-checkboxes input.country-cb").prop("checked", true);
        updateChart();
    });

    jQuery("#clear-countries").on("click", function () {
        jQuery("#country-checkboxes input.country-cb").prop("checked", false);
        updateChart();
    });

    initializePym();
});
