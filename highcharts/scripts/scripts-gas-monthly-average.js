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
        jQuery.getJSON("data/monthly_demand_average.json", function (data) {
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
    
        // Collect all group values
        groupBValues.forEach(group_b_value => {
            Object.keys(data[group_b_value]).forEach(group_value => groupValues.add(group_value));
        });
    
        // Populate country selector
        $groupBSelector.empty();
        groupBValues.forEach(group_b_value => {
            $groupBSelector.append(`<option value="${group_b_value}">${group_b_value}</option>`);
        });
    
        // Set default selected country
        const defaultGroupBValue = "EU";
        if (groupBValues.includes(defaultGroupBValue)) {
            $groupBSelector.val(defaultGroupBValue);
        }
    
// Convert set to array and sort alphabetically
        let sortedGroupValues = [...groupValues].sort((a, b) => a.localeCompare(b));

// Ensure "Total" is first
        if (sortedGroupValues.includes("total")) {
            sortedGroupValues = sortedGroupValues.filter(value => value !== "total");
            sortedGroupValues.unshift("total");
        }

// Ensure "industry-household" is last
        if (sortedGroupValues.includes("industry-household")) {
            sortedGroupValues = sortedGroupValues.filter(value => value !== "industry-household");
            sortedGroupValues.push("industry-household");
        }

    
        // Populate type selector
        $groupSelector.empty();
        sortedGroupValues.forEach(group_value => {
            $groupSelector.append(`<option value="${group_value}">${group_value}</option>`);
        });
    
        // Add event listeners
        $groupBSelector.change(() => filterGroupSelector(data));
        $groupSelector.change(() => updateChart());
    
        // Initialize filtered selector
        filterGroupSelector(data);
    }
    
    function filterGroupSelector(data) {
        const selectedGroupBValue = jQuery("#country-select").val();
        const $groupSelector = jQuery("#type-select");
        $groupSelector.empty();
    
        if (selectedGroupBValue && data[selectedGroupBValue]) {
            let groupValues = Object.keys(data[selectedGroupBValue]).sort((a, b) => a.localeCompare(b));
        
            // Ensure "Total" is first
            if (groupValues.includes("total")) {
                groupValues = groupValues.filter(value => value !== "total");
                groupValues.unshift("total");
            }
        
            // Ensure "industry-household" is last
            if (groupValues.includes("industry-household")) {
                groupValues = groupValues.filter(value => value !== "industry-household");
                groupValues.push("industry-household");
            }
        
            // Populate the type selector
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
            "2024": "#5E8FE0",
            "2023": "#C0392B",
            "2022": "#C0392B80",
            "AVG-2019-2021": "#A6A6A6",
        };
    
        return Object.keys(data).map(x_value => ({
            name: `${x_value}`,
            data: data[x_value].map(entry => ({ x: entry.x_b_value, y: entry.y_value })),
            color: colorMap[x_value] || "#999",
            dashStyle: x_value === "AVG-2019-2021" ? "ShortDot" : "Solid", // Apply ShortDot for AVG line
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
                    enabled: false, // ❌ Removes the range selector
                },
                navigator: {
                    enabled: false, // ❌ Removes the zooming navigator
                },
                scrollbar: {
                    enabled: false, // ❌ Removes the bottom scrollbar
                },
                chart: {
                    type: "line",
                },
                title: {
                    text: "Monthly natural gas demand (TWh)",
                    align: "left",
                    style: { fontWeight: "bold",
                        fontSize: '20px'
                     },
                },
                subtitle: {
                    text: subtitleText,
                    align: "left",
                    style: { color: "grey",
                        fontSize: '15px'
                     },
                },
                legend: {
                    enabled: true,
                    align: "center",
                    verticalAlign: "top",
                    layout: "horizontal",
                    itemStyle: {
                        fontSize: "15px", 

                        color: "#333", 
                    },
                    itemMarginBottom: 5,
                    maxHeight: 200,
                    navigation: {
                        enabled: true,
                    },
                    labelFormatter: function () {
                        return this.name.split(" - ").pop();
                    },
                    symbolHeight: 10,   // Ensure symbols have a proper height
                    symbolWidth: 10,    // Make them square
                    symbolRadius: 50,   // Increase radius to make it look like a bubble
                    itemDistance: 15,  
                    backgroundColor: "rgba(255, 255, 255, 0.7)", 
                    borderRadius: 10, 
                    padding: 8,
                },
                
                plotOptions: {
                    series: {
                        showInLegend: true,
                        marker: {
                            enabled: true,   // 🔹 Ensures the legend uses markers instead of line styles
                            radius: 6,       // 🔹 Sets a fixed radius for the "bubble" effect
                            symbol: "circle" // 🔹 Forces a circular marker
                        },
                    },
                },
                               
                xAxis: {
                    type: "linear",
                    labels: {
                        formatter: function () {
                            const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                            return months[this.value - 1] || this.value; // Convert numbers to month names
                        },
                    },
                    tickInterval: 1,
                    minTickInterval: 1,
                    tickPixelInterval: 50,
                },
                yAxis: {
                    title: {
                        text: "TWh"
                    },
                    labels: {
                        align: "left",
                    },
                    min: 0, // 🔹 Ensures the y-axis starts at zero
                    height: "100%",
                    resize: {
                        enabled: true,
                    },
                },
                
                tooltip: {
                    split: true,
                    valueDecimals: 2,
                    formatter: function () {
                        const months = ["Jan", "Fev", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                        const monthIndex = this.x - 1;
                        const monthName = months[monthIndex] || this.x;
                
                        return `<b>${monthName}</b><br/>` +
                            this.points.map(point => 
                                `<span style="color:${point.series.color}">${point.series.name}</span>: <b>${point.y.toFixed(0)} TWh</b><br/>`
                            ).join('');
                    }
                },
                plotOptions: {
                    series: {
                        showInNavigator: false, // ❌ Ensure series don't show in navigator
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
