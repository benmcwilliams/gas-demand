jQuery(document).ready(function () {
    let pymChild;
    let chart;
    let fullData = {}; // Store the fetched data globally

    function initializePym() {
        console.log("Initializing Pym.js");
        pymChild = new pym.Child({ polling: 100, debug: true });

        const updateSize = () => {
            console.log("Updating size of main container");
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
        console.log("Fetching data from JSON file");
        jQuery.getJSON("data/weekly_demand.json", function (data) {
            console.log("Data fetched successfully", data);
            fullData = groupDataByCountryAndType(data);
            callback(fullData);
        }).fail(function () {
            console.error("Error loading the JSON file.");
        });
    }

    function groupDataByCountryAndType(data) {
        console.log("Grouping data by group_b_value and group_value");
        return data.reduce((acc, entry) => {
            const { group_b_value, group_value, x_value, x_b_value, y_value } = entry;
            if (!acc[group_b_value]) acc[group_b_value] = {};
            if (!acc[group_b_value][group_value]) acc[group_b_value][group_value] = {};
            if (!acc[group_b_value][group_value][x_value]) acc[group_b_value][group_value][x_value] = [];
            acc[group_b_value][group_value][x_value].push({ x_b_value: parseInt(x_b_value, 10), y_value });
            return acc;
        }, {});
    }

    function populateSelectors(data) {
        console.log("Populating selectors");
        const $groupBSelector = jQuery("#country-select");
        const $groupSelector = jQuery("#type-select");
    
        const groupBValues = Object.keys(data);
        const groupValues = new Set();
        groupBValues.forEach(group_b_value => {
            Object.keys(data[group_b_value]).forEach(group_value => groupValues.add(group_value));
        });
    
        groupBValues.forEach(group_b_value => {
            $groupBSelector.append(`<option value="${group_b_value}">${group_b_value}</option>`);
        });
    
        const defaultGroupBValue = "Europe*";
        if (groupBValues.includes(defaultGroupBValue)) {
            $groupBSelector.val(defaultGroupBValue);
        }
    
        groupValues.forEach(group_value => {
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
            const groupValues = Object.keys(data[selectedGroupBValue]);
            groupValues.forEach(group_value => {
                $groupSelector.append(`<option value="${group_value}">${group_value}</option>`);
            });
        }

        updateChart();
    }

    function formatSeriesData(group_b_value, group_value) {
        console.log("Formatting series data for", { group_b_value, group_value });
        if (!group_b_value || !group_value || !fullData[group_b_value] || !fullData[group_b_value][group_value]) {
            return [];
        }

        const data = fullData[group_b_value][group_value];
        const colorMap = {
            "2025": "#880E4F",
            "2024": "#a21636",
            "2023": "#EF9A9A",
            "2022": "#F2D1D3",
            "AVG-2019-2021": "#A6A6A6",
        };

        return Object.keys(data).map(x_value => ({
            name: `${x_value}`,
            data: data[x_value].map(entry => ({ x: entry.x_b_value, y: entry.y_value })),
            color: colorMap[x_value] || "#999",
            marker: { enabled: false },
        }));
    }

    function updateChart() {
        const group_b_value = jQuery("#country-select").val();
        const group_value = jQuery("#type-select").val();
        console.log("Updating chart for", { group_b_value, group_value });
    
        const series = formatSeriesData(group_b_value, group_value);
    
        const subtitleText = group_b_value
            ? `${group_b_value} - ${group_value} (2019-21 average, 2021 to 2025)`
            : "2019-2021 Average, 2022 to 2025";
    
        if (!chart) {
            chart = Highcharts.stockChart("chart-container", {
                rangeSelector: {
                    selected: 0,
                    buttons: [
                        {
                            type: "all",
                            text: "-",
                        },
                    ],
                    inputEnabled: false,
                },
                chart: {
                    type: "line",
                },
                title: {
                    text: "Weekly natural gas demand (TWh)",
                    align: "left",
                    style: { fontWeight: "bold" },
                },
                subtitle: {
                    text: subtitleText,
                    align: "left",
                    style: { color: "grey" },
                },
                legend: {
                    enabled: true,
                    align: "center",
                    verticalAlign: "top",
                    layout: "horizontal",
                    itemStyle: {
                        fontSize: "9px",
                        fontWeight: "normal",
                    },
                    itemMarginBottom: 0,
                    maxHeight: 200,
                    navigation: {
                        enabled: true,
                    },
                    labelFormatter: function () {
                        return this.name.split(" - ").pop();
                    },
                    symbolRadius: 10,
                },
                xAxis: {
                    type: "linear",  
                    labels: {
                        formatter: function () {
                            return this.value; // Ensure x_b_value is shown as is
                        },
                    },
                    tickInterval: 1, // Reduce tick interval to show more graduations
                    minTickInterval: 1, // Ensures at least one tick per value
                    tickPixelInterval: 50, // Reduce spacing between ticks
                },
                
                yAxis: {
                    title: {
                        text: "TWh"
                    },
                    labels: {
                        align: "left",
                    },
                    height: "80%",
                    resize: {
                        enabled: true,
                    },
                },
                tooltip: {
                    split: true,
                    valueDecimals: 2,
                    headerFormat: "Week: {point.x}<br/>",
                    pointFormat:
                        "<span style=\"color:{series.color}\">{series.name}</span>: <b>{point.y:.2f} TWh</b><br/>",
                },
                navigator: {
                    xAxis: { labels: { enabled: false }, tickLength: 0 },
                },
                plotOptions: {
                    series: {
                        showInNavigator: true,
                        marker: {
                            enabled: false,
                        },
                    },
                },
                exporting: {
                    enabled: true,
                    sourceWidth: 1000,
                    sourceHeight: 1000,
                    scale: 1,
                    csv: {
                        itemDelimiter: ";",
                        lineDelimiter: "\n",
                        decimalPoint: ",",
                    },
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
                series: series,
            });
        } else {
            while (chart.series.length > 0) chart.series[0].remove(false);
            series.forEach((s) => chart.addSeries(s, false));
            chart.setTitle(null, { text: subtitleText });
            chart.redraw();
        }
    }

    

    fetchData(data => {
        populateSelectors(data);
        updateChart(); // Initialize chart with default values
    });

    initializePym();
});
