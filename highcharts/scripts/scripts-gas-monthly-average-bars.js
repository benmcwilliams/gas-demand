jQuery(document).ready(function () {
    (function waitHighcharts(ready) {
        if (typeof Highcharts !== "undefined") return ready();
        window.addEventListener("highcharts:ready", ready, { once: true });
    })(function () {
        let pymChild;
        let chart;
        let fullData = {};

        const MONTH_LABELS = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ];

        function initializePym() {
            pymChild = new pym.Child({ polling: 100, debug: false });
            const updateSize = () => {
                const containerWidth = Math.min(window.innerWidth, 1000);
                const containerHeight = window.innerHeight * 1;
                jQuery("#main-container").css({
                    width: `${containerWidth}px`,
                    height: `${containerHeight}px`,
                });
                pymChild.sendHeight(containerHeight);
            };
            setTimeout(updateSize, 500);
            window.addEventListener("resize", updateSize);
        }

        function fetchData(callback) {
            jQuery.getJSON("data/monthly_demand_average.json", function (data) {
                fullData = groupDataByCountryAndType(data);
                callback(fullData);
            }).fail(function () {
                console.error("Error loading data/monthly_demand_average.json");
            });
        }

        function groupDataByCountryAndType(data) {
            return data.reduce((acc, entry) => {
                const { group_b_value, group_value, x_value, x_b_value, y_value } = entry;
                if (!acc[group_b_value]) acc[group_b_value] = {};
                if (!acc[group_b_value][group_value]) acc[group_b_value][group_value] = {};
                if (!acc[group_b_value][group_value][x_value]) acc[group_b_value][group_value][x_value] = [];
                acc[group_b_value][group_value][x_value].push({
                    x_b_value: parseInt(x_b_value, 10),
                    y_value,
                });
                return acc;
            }, {});
        }

        function populateSelectors(data) {
            const $groupBSelector = jQuery("#country-select");
            const $groupSelector = jQuery("#type-select");

            const groupBValues = Object.keys(data);
            const groupValues = new Set();

            groupBValues.forEach((group_b_value) => {
                Object.keys(data[group_b_value]).forEach((group_value) => groupValues.add(group_value));
            });

            $groupBSelector.empty();
            groupBValues.forEach((group_b_value) => {
                $groupBSelector.append(`<option value="${group_b_value}">${group_b_value}</option>`);
            });

            if (groupBValues.includes("EU")) {
                $groupBSelector.val("EU");
            }

            let sortedGroupValues = [...groupValues].sort((a, b) => a.localeCompare(b));
            if (sortedGroupValues.includes("total")) {
                sortedGroupValues = sortedGroupValues.filter((value) => value !== "total");
                sortedGroupValues.unshift("total");
            }
            if (sortedGroupValues.includes("industry-household")) {
                sortedGroupValues = sortedGroupValues.filter((value) => value !== "industry-household");
                sortedGroupValues.push("industry-household");
            }

            $groupSelector.empty();
            sortedGroupValues.forEach((group_value) => {
                $groupSelector.append(`<option value="${group_value}">${group_value}</option>`);
            });

            $groupBSelector.change(() => filterGroupSelector(data));
            $groupSelector.change(() => updateChart());
            filterGroupSelector(data);
        }

        function filterGroupSelector(data) {
            const selectedGroupBValue = jQuery("#country-select").val();
            const $groupSelector = jQuery("#type-select");
            $groupSelector.empty();

            if (selectedGroupBValue && data[selectedGroupBValue]) {
                let groupValues = Object.keys(data[selectedGroupBValue]).sort((a, b) => a.localeCompare(b));
                if (groupValues.includes("total")) {
                    groupValues = groupValues.filter((value) => value !== "total");
                    groupValues.unshift("total");
                }
                if (groupValues.includes("industry-household")) {
                    groupValues = groupValues.filter((value) => value !== "industry-household");
                    groupValues.push("industry-household");
                }
                groupValues.forEach((group_value) => {
                    $groupSelector.append(`<option value="${group_value}">${group_value}</option>`);
                });
            }
            updateChart();
        }

        function getLatestCalendarYearKey(seriesByYear) {
            const keys = Object.keys(seriesByYear).filter((k) => /^\d{4}$/.test(k));
            if (!keys.length) return null;
            return String(Math.max(...keys.map((k) => parseInt(k, 10))));
        }

        /** 12 values per series (null if missing) for category xAxis */
        function pointsToMonthlyArray(sortedPoints) {
            const byMonth = {};
            sortedPoints.forEach((p) => {
                byMonth[p.x_b_value] = p.y_value;
            });
            const arr = [];
            for (let m = 1; m <= 12; m++) {
                arr.push(byMonth[m] != null ? byMonth[m] : null);
            }
            return arr;
        }

        function formatColumnSeries(group_b_value, group_value) {
            if (!group_b_value || !group_value || !fullData[group_b_value] || !fullData[group_b_value][group_value]) {
                return [];
            }

            const data = fullData[group_b_value][group_value];
            const latestKey = getLatestCalendarYearKey(data);

            const keysOrder = [];
            if (data["AVG-2019-2021"]) keysOrder.push("AVG-2019-2021");
            if (data["AVG-2022-2025"]) keysOrder.push("AVG-2022-2025");
            if (latestKey && data[latestKey]) keysOrder.push(latestKey);

            const displayName = (k) => {
                if (k === "AVG-2019-2021") return "2019–2021 avg";
                if (k === "AVG-2022-2025") return "2022–2025 avg";
                return k;
            };

            return keysOrder.map((x_value) => {
                const sorted = data[x_value].slice().sort((a, b) => a.x_b_value - b.x_b_value);
                return {
                    type: "column",
                    name: displayName(x_value),
                    data: pointsToMonthlyArray(sorted),
                    color:
                        x_value === "AVG-2019-2021"
                            ? "#757575"
                            : x_value === "AVG-2022-2025"
                              ? "#1565C0"
                              : "#880E4F",
                };
            });
        }

        function updateChart() {
            const group_b_value = jQuery("#country-select").val();
            const group_value = jQuery("#type-select").val();

            const series = formatColumnSeries(group_b_value, group_value);
            const bucket = fullData[group_b_value]?.[group_value];
            const latestKey = bucket ? getLatestCalendarYearKey(bucket) : null;

            const subtitleText = group_b_value
                ? `${group_b_value} - ${group_value} (2019–21 avg, 2022–25 avg${latestKey ? ", " + latestKey : ""})`
                : "2019–21 avg, 2022–25 avg vs latest year";

            const chartOptions = {
                chart: {
                    type: "column",
                },
                title: {
                    text: "Monthly natural gas demand (TWh) — clustered bars",
                    align: "left",
                    style: { fontWeight: "bold", fontSize: "20px" },
                },
                subtitle: {
                    text: subtitleText,
                    align: "left",
                    style: { color: "grey", fontSize: "15px" },
                },
                legend: {
                    enabled: true,
                    align: "center",
                    verticalAlign: "top",
                    layout: "horizontal",
                },
                xAxis: {
                    categories: MONTH_LABELS,
                    crosshair: true,
                    labels: {
                        style: { fontSize: "12px" },
                    },
                },
                yAxis: {
                    min: 0,
                    title: { text: "TWh" },
                    labels: { align: "left" },
                },
                plotOptions: {
                    column: {
                        borderWidth: 0,
                        groupPadding: 0.12,
                        pointPadding: 0.02,
                        dataLabels: { enabled: false },
                    },
                },
                tooltip: {
                    shared: true,
                    valueDecimals: 2,
                    headerFormat: "<b>{point.key}</b><br/>",
                    pointFormat:
                        '<span style="color:{series.color}">\u25CF</span> {series.name}: <b>{point.y:.1f}</b> TWh<br/>',
                },
                exporting: {
                    enabled: true,
                    buttons: {
                        contextButton: {
                            menuItems: ["viewFullscreen", "printChart", "downloadPNG", "downloadCSV"],
                        },
                    },
                },
                series,
            };

            if (!chart) {
                chart = Highcharts.chart("chart-container", chartOptions);
            } else {
                while (chart.series.length > 0) {
                    chart.series[0].remove(false);
                }
                chart.update(
                    {
                        subtitle: { text: subtitleText },
                        xAxis: { categories: MONTH_LABELS },
                    },
                    false
                );
                series.forEach((s) => chart.addSeries(s, false));
                chart.redraw();
            }
        }

        fetchData((data) => {
            populateSelectors(data);
            updateChart();
        });

        initializePym();
    });
});
