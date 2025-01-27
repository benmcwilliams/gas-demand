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
        jQuery.getJSON("highcharts/data/weekly_demand_clean.json", function (data) {
            console.log("Data fetched successfully", data);
            fullData = groupDataByCountryAndType(data);
            callback(fullData);
        }).fail(function () {
            console.error("Error loading the JSON file.");
        });
    }

    function groupDataByCountryAndType(data) {
        console.log("Grouping data by country and type");
        return data.reduce((acc, entry) => {
            const { country, type, year, week, demand } = entry;
            if (!acc[country]) acc[country] = {};
            if (!acc[country][type]) acc[country][type] = {};
            if (!acc[country][type][year]) acc[country][type][year] = [];
            acc[country][type][year].push({ week: parseInt(week, 10), demand });
            return acc;
        }, {});
    }

    function populateSelectors(data) {
        console.log("Populating selectors");
        const $countrySelector = jQuery("#country-select");
        const $typeSelector = jQuery("#type-select");
    
        // Collect unique combinations of country and type
        const countries = Object.keys(data);
        const types = new Set();
        countries.forEach(country => {
            Object.keys(data[country]).forEach(type => types.add(type));
        });
    
        // Populate country selector
        countries.forEach(country => {
            $countrySelector.append(`<option value="${country}">${country}</option>`);
        });
    
        // Set default country to "Europe" if it exists
        const defaultCountry = "Europe*"; // Replace with your desired default
        if (countries.includes(defaultCountry)) {
            $countrySelector.val(defaultCountry);
        }
    
        // Populate type selector
        types.forEach(type => {
            $typeSelector.append(`<option value="${type}">${type}</option>`);
        });
    
        $countrySelector.change(() => filterTypeSelector(data));
        $typeSelector.change(() => updateChart());
    
        // Trigger the initial filter for the default country
        filterTypeSelector(data);
    }
    

    function filterTypeSelector(data) {
        const selectedCountry = jQuery("#country-select").val();
        const $typeSelector = jQuery("#type-select");
        $typeSelector.empty(); // Clear current options

        if (selectedCountry && data[selectedCountry]) {
            const types = Object.keys(data[selectedCountry]);
            types.forEach(type => {
                $typeSelector.append(`<option value="${type}">${type}</option>`);
            });
        }

        updateChart(); // Update the chart based on new selection
    }

    function formatSeriesData(country, type) {
        console.log("Formatting series data for", { country, type });
        if (!country || !type || !fullData[country] || !fullData[country][type]) {
            return [];
        }

        const data = fullData[country][type];
        const colorMap = {
            "2025": "#880E4F",
            "2024": "#a21636",
            "2023": "#EF9A9A",
            "2022": "#F2D1D3",
            "AVG-2019-2021": "#A6A6A6",
        };

        return Object.keys(data).map(year => ({
            name: `${year}`,
            data: data[year].map(entry => ({ x: entry.week, y: entry.demand })),
            color: colorMap[year] || "#999",
            marker: { enabled: false },
        }));
    }

    function updateChart() {
        const country = jQuery("#country-select").val();
        const type = jQuery("#type-select").val();
        console.log("Updating chart for", { country, type });
    
        const series = formatSeriesData(country, type);
    
        // Construct the subtitle text dynamically based on the selected country
        const subtitleText = country
            ? `${country} - ${type} (2019-21 average, 2021 to 2025)`
            : "2019-2021 Average, 2022 to 2025";
    
        if (!chart) {
            chart = Highcharts.stockChart("chart-container", {
                rangeSelector: {
                    selected: 0, // Automatically selects the "All" button on initialization
                    buttons: [
                        {
                            type: "all",
                            text: "-", // Default to "All" view
                        },
                    ],
                    inputEnabled: false, // Disable date input fields
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
                        return this.name.split(" - ").pop(); // Extract year from series name
                    },
                    symbolRadius: 10, // Circular legend symbols
                },
                xAxis: {
                    type: "datetime",
                    tickInterval: 3 * 30 * 24 * 3600 * 1000, // 3-month intervals
                    labels: {
                        formatter: function () {
                            return Highcharts.dateFormat("%b %Y", this.value); // Display as "Jan 2022"
                        },
                    },
                    tickPixelInterval: 150,
                },
                yAxis: {
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
                            enabled: false, // Disable points globally
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
            // Update existing chart
            while (chart.series.length > 0) chart.series[0].remove(false);
            series.forEach((s) => chart.addSeries(s, false));
            chart.setTitle(null, { text: subtitleText }); // Update the subtitle
            chart.redraw();
        }
    }
    

    fetchData(data => {
        populateSelectors(data);
        updateChart(); // Initialize chart with default values
    });

    initializePym();
});
