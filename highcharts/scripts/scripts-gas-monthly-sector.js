$(document).ready(function() {  
    let pymChild;

    function initializePym() {
        pymChild = new pym.Child({ polling: 100, debug: true });

        const updateSize = () => {
            const containerWidth = Math.min(window.innerWidth, 1000);
            const containerHeight = window.innerHeight * 1;
            jQuery("#main-container").css({
                width: `${containerWidth}px`,
                height: `${containerHeight}px`
            });
            pymChild.sendHeight(containerHeight);
            pymChild.sendWidth(containerWidth);
        };

        setTimeout(updateSize, 500);
        window.addEventListener('resize', updateSize);
    }

    function fetchData(filePath, callback) {
        const selectedGroupBValue = $('#trade-select').val() || "Net exports"; // Default to "Net exports"
        $.getJSON(filePath, function(data) {
            const filteredData = data.filter(entry => entry.group_b_value === selectedGroupBValue); // Filter by group_b_value
            const groupedData = groupDataByGroupValue(filteredData);
            callback(groupedData);
        }).fail(function() {
            console.error("Error loading the JSON file from:", filePath);
        });
    }

    function groupDataByGroupValue(data) {
        const groupedData = {};
        data.forEach(entry => {
            const groupValue = entry.group_value.trim();
            if (!groupedData[groupValue]) {
                groupedData[groupValue] = [];
            }
            groupedData[groupValue].push({
                x_value: entry.x_value,
                y_value: entry.y_value
            });
        });
        return groupedData;
    }

    function createChart(data, subtitleText = 'Europe (2022 to 2025 vs 2019-21 monthly average)') {
        const selectedGroupBValue = $('#trade-select').val() || ""; // Get selected group_b_value
        const isNetExports = selectedGroupBValue === ""; // Check if "Net exports" is selected
    
        const series = Object.keys(data).map((groupValue, index) => {
            const color = getColorFromCSS(cssColorVars[index]);
            return {
                name: groupValue,
                data: formatSeriesData(data[groupValue]),
                visible: index < 7, // Default visibility for first 7 series
                color: color,
                stack: 'groupValues'
            };
        });
    
        const chart = Highcharts.chart('chart-container', {
            chart: {
                type: 'column',
                height: 'auto',
                events: {
                    load: function () {
                        addExportsLabel(this);
                    },
                    redraw: function () {
                        addExportsLabel(this);
                    }
                }                              
            },
            title: {
                text: 'Monthly Gas Demand by sector (TWh) ',
                align: 'left'
            },
            subtitle: {
                text: subtitleText,
                align: 'left'
            },
            yAxis: {
                title: {
                    text: 'TWh'
                },
            },                       
            xAxis: {
                type: 'datetime',
                dateTimeLabelFormats: {
                    month: '%b %Y'
                },
                tickInterval: 3 * 30 * 24 * 60 * 60 * 1000, // 3 months in milliseconds
                min: Date.UTC(2022, 0, 1)
            },
            tooltip: {
                headerFormat: '<b>{series.name}</b><br>',
                pointFormat: '{point.x:%b %Y}: {point.y:.3f} TWh'
            },
            plotOptions: {
                column: {
                    stacking: 'normal',
                    dataLabels: {
                        enabled: false
                    },
                    pointPadding: 0.01,
                    groupPadding: 0.01,
                    borderWidth: 0
                }
            },
            legend: {
                enabled: true
            },
            series: series,
            exporting: {
                enabled: true,
                csv: {
                    itemDelimiter: ';',
                    lineDelimiter: '\n',
                    decimalPoint: ','
                },
                buttons: {
                    contextButton: {
                        menuItems: [
                            'viewFullscreen',
                            'printChart',
                            'downloadCSV'
                        ]
                    }
                }
            }
        });
    
        // Add custom legend for toggling series visibility
        createCustomLegend(chart);
    }
    
    function addExportsLabel(chart) {
        // Remove existing custom labels if any
        if (chart.customYAxisLabels) {
            chart.customYAxisLabels.forEach(label => label.destroy());
        }
        chart.customYAxisLabels = [];
    
        const yAxis = chart.yAxis[0];
        const extremes = yAxis.getExtremes();
        const lastValue = extremes.max; // Get the last value on the Y-axis
        const lastValuePosition = yAxis.toPixels(lastValue, true); // Y position of the last value
    
        // Debugging logs
        console.log("Y-Axis extremes:", extremes);
        console.log("Last value on Y-axis:", lastValue);
        console.log("Last value position (pixels):", lastValuePosition);
    
        // Ensure the label is within the visible chart area
        if (lastValuePosition > 0 && lastValuePosition < chart.chartHeight) {
            // Adjust for chart margins
            const labelX = chart.plotLeft + chart.plotWidth - 1; // Align near the right edge
            const labelY = Math.min(
                Math.max(lastValuePosition - 1, chart.plotTop), // Ensure it's above the top margin
                chart.plotTop + chart.plotHeight - 1// Ensure it's below the bottom margin
            );
            console.log("Adjusted label position:", labelX, labelY);
    
            const exportsLabel = chart.renderer.text('Exports', labelX, labelY)
                .attr({
                    align: 'right'
                })
                .css({
                    color: '#000',
                    fontSize: '12px',
                    fontWeight: 'bold'
                })
                .add();
    
            chart.customYAxisLabels.push(exportsLabel);
        } else {
            console.warn("Exports label is outside the chart area or not rendered");
        }
    }

    function formatSeriesData(groupValueData) {
        return groupValueData.map(entry => {
            const [xValueMonth, xValueYear] = entry.x_value.split('/');
            return {
                x: Date.UTC(xValueYear, xValueMonth - 1, 1), // Use Date.UTC to avoid timezone issues
                y: parseFloat(entry.y_value)
            };
        });
    }
    

    function getColorFromCSS(variableName) {
        return getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
    }

    const cssColorVars = [
        '--item-color12', '--item-color13', '--item-color20', '--item-color25', '--item-color14','--item-color30', '--item-color1'
    ];

    function createCustomLegend(chart) {
        const $legendContainer = $('#legend-container');
        reorderLegendItems(chart);
    }
    
    function reorderLegendItems(chart) {
        const $legendContainer = jQuery('#legend-container');
        $legendContainer.empty();

        const $hideAllButton = jQuery('<button id="hide-all" class="toggle-button">').text('Reset').appendTo($legendContainer);

        $hideAllButton.click(function() {
            chart.series.forEach(series => series.setVisible(false, false));
            chart.redraw(); // Ensure the chart is redrawn
            reorderLegendItems(chart);
        });

        // Sort the series based on visibility and legendIndex
        const sortedSeries = chart.series.slice().sort((a, b) => {
            return b.visible - a.visible || b.legendIndex - a.legendIndex;
        });

        jQuery.each(sortedSeries, function(i, series) {
            const $legendItem = jQuery('<div>')
                .addClass('legend-item')
                .css({ cursor: 'pointer' })
                .appendTo($legendContainer);

            const $checkbox = jQuery('<input type="checkbox" />')
                .prop('checked', series.visible)
                .css({ marginRight: '10px' })
                .appendTo($legendItem);

            jQuery('<span>').html(series.name).appendTo($legendItem);

            // Attach a click handler to the entire legend item
            $legendItem.click(function() {
                const isVisible = !series.visible;
                series.setVisible(isVisible, false);
                $checkbox.prop('checked', isVisible);
                series.legendIndex = Date.now(); // Update the legendIndex to reorder
                reorderLegendItems(chart);
                assignColorsToSeries(chart.series);
                chart.redraw(); // Ensure the chart is redrawn and bars are re-stacked
            });

            // Prevent checkbox click event from triggering the parent click handler
            $checkbox.click(function(event) {
                event.stopPropagation();
                series.setVisible(this.checked, false);
                series.legendIndex = Date.now(); // Update the legendIndex to reorder
                reorderLegendItems(chart);
                assignColorsToSeries(chart.series);
                chart.redraw(); // Ensure the chart is redrawn and bars are re-stacked
            });
        });

        // Redraw the chart to recalculate stacking and visibility
        chart.redraw();

        if (typeof pymChild !== 'undefined') pymChild.sendHeight();
    }

    $('#trade-select').on('change', function() {
        const selectedGroupBValue = $('#trade-select').val() || "Net exports"; // Get the selected value
        const subtitleText = `${selectedGroupBValue} (2021-2025 vs 2019-2021 monthly average)`; // Dynamic subtitle
    
        // Fetch the data and recreate the chart
        fetchData('data/monthly_demand_sector.json', function(groupedData) {
            createChart(groupedData, subtitleText);
        });
    });

    // Initial chart rendering
    fetchData('data/monthly_demand_sector.json', createChart);
    initializePym();
});
