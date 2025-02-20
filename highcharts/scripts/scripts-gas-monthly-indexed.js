jQuery(document).ready(function() { 
    let pymChild;

    function initializePym() {
        pymChild = new pym.Child({ polling: 100, debug: true });

        // Function to set initial height and width to fit the parent’s #main-container dimensions
        const updateSize = () => {
            const containerWidth = Math.min(window.innerWidth, 1000); // Match parent max-width
            const containerHeight = window.innerHeight * 1; // Match parent height
            jQuery("#main-container").css({
                width: `${containerWidth}px`,
                height: `${containerHeight}px`
            });
            pymChild.sendHeight(containerHeight); // Send a fixed height instead of dynamic resizing
            pymChild.sendWidth(containerWidth);
        };

        // Set initial size
        setTimeout(updateSize, 500);

        // Optional: Listen for window resize to reapply the fixed dimensions
        window.addEventListener('resize', updateSize);
    }

    function fetchData(callback) {
        let demandData = {};
        let targetData = {};
    
        jQuery.getJSON('data/monthly_demand_indexed.json', function(data) {
            demandData = groupDataByGroupValue(data);
    
            // Fetch the fixed target lines separately
            jQuery.getJSON('data/targets.json', function(targets) {
                targetData = processTargetData(targets);
                callback(demandData, targetData); // Pass both datasets to the chart function
            }).fail(function() {
                console.error("Error loading the targets JSON file.");
            });
    
        }).fail(function() {
            console.error("Error loading the monthly demand JSON file.");
        });
    }

    function processTargetData(targets) {
        return {
            "Fit for 55": targets.map(t => ({
                x: new Date(t.year, t.month - 1).getTime(),
                y: t.fit
            })),
            "REPowerEU": targets.map(t => ({
                x: new Date(t.year, t.month - 1).getTime(),
                y: t.REPowerEU
            }))
        };
    }
    

    function groupDataByGroupValue(data) {
        return data.reduce((acc, entry) => {
            const groupValue = entry.group_value.trim();
            if (!acc[groupValue]) acc[groupValue] = [];
            acc[groupValue].push({
                x_value: entry.x_value,
                y_value: entry.y_value
            });
            return acc;
        }, {});
    }

    function formatSeriesData(groupData) {
        return groupData.map(entry => ({
            x: new Date(...entry.x_value.split('/').reverse()).getTime(),
            y: parseFloat(entry.y_value)
        }));
    }

    function getColorFromCSS(variableName) {
        return getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
    }

    const cssColorVars = Array.from({ length: 30 }, (_, i) => `--item-color${i + 1}`);
   
    function assignColorsToSeries(series) {
        const visibleSeries = series.filter(s => s.visible);
        visibleSeries.forEach((s, index) => {
            if (s.name === "REPowerEU" || s.name === "Fit for 55" || s.name === "EU") return; // <<< Skip "REPowerEU", "Fit for 55", and "EU" to preserve their colors
    
            const colorVariable = cssColorVars[index % cssColorVars.length];
            const newColor = getColorFromCSS(colorVariable);
            s.update({
                color: newColor,
                marker: {
                    fillColor: newColor,
                    lineColor: newColor
                },
                dataLabels: {
                    style: { color: newColor }
                }
            }, false);
        });
        series[0].chart.redraw();
    }
    
    

    function reorderLegendItems(chart) {
        const $legendContainer = jQuery('#legend-container');
        $legendContainer.empty();
    
        
        const $hideAllButton = jQuery('<button id="hide-all" class="toggle-button">').text('Reset').appendTo($legendContainer);
    
        
        $hideAllButton.click(function() {
            chart.series.forEach(series => {
                if (series.name !== "Fit for 55" && series.name !== "REPowerEU" && series.name !== "EU") {
                    series.setVisible(false, false);
                } else {
                    series.setVisible(true, false); // Ensure "EU - total", "Fit for 55", and "REPowerEU" remain visible
                }
            });
            chart.redraw();
            reorderLegendItems(chart);
        });
        
        
    
        const sortedSeries = chart.series.slice()
        .filter(s => s.options.showInLegend === false) // Only include series meant for checkboxes
        .sort((a, b) => b.visible - a.visible || b.legendIndex - a.legendIndex);
    
        
    
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
                series.legendIndex = Date.now();
                reorderLegendItems(chart);
                assignColorsToSeries(chart.series);
            });
    
            // Prevent checkbox click event from triggering the parent click handler
            $checkbox.click(function(event) {
                event.stopPropagation();
                series.setVisible(this.checked, false);
                series.legendIndex = Date.now();
                reorderLegendItems(chart);
                assignColorsToSeries(chart.series);
            });
        });
    }
    
    function createChart(data, targetData) {
        const series = Object.keys(data).map((groupValue, i) => {
            const assignedColor = groupValue === "EU" ? "#155866" : getColorFromCSS(cssColorVars[i]); // Ensure "EU" gets its fixed color
        
            return {
                name: groupValue,
                data: formatSeriesData(data[groupValue]),
                visible: groupValue === "EU",
                color: assignedColor, // <<< Fixed color for "EU"
                marker: { enabled: false }, 
                showInLegend: false, // Exclude from Highcharts legend (keeps it in checkboxes)
                dataLabels: {
                    enabled: true,
                    align: 'left',
                    style: { 
                        fontWeight: 'bold', 
                        fontFamily: 'Roboto', 
                        textOutline: 'none', 
                        fontSize: '12px', 
                        color: assignedColor // <<< Ensure data labels use the same color
                    },
                    formatter: function() {
                        return this.point.index === this.series.data.length - 1 ? this.series.name : null;
                    },
                    x: 10, 
                    y: 0, 
                    crop: false, 
                    overflow: 'allow', 
                    allowOverlap: true
                }
            };
        });
        
        
        
        series.push(
            {
                name: "Fit for 55",
                data: targetData["Fit for 55"],
                color: "#FFC000", // <<< Fixed yellow color for "Fit for 55"
                visible: true,
                enableMouseTracking: true,
                lineWidth: 2,
                dashStyle: "ShortDot",
                marker: { enabled: false },
                showInLegend: true, // <<< Keep it out of the Highcharts legend
                dataLabels: {
                    enabled: false
                }
            },
            {
                name: "REPowerEU",
                data: targetData["REPowerEU"],
                color: "#a21636", // <<< Fixed red color for "REPowerEU"
                visible: true,
                enableMouseTracking: true,
                lineWidth: 2,
                dashStyle: "ShortDot",
                marker: { enabled: false },
                showInLegend: true, // <<< Only "REPowerEU" appears in the legend
                dataLabels: {
                    enabled: false
                }
            }
        );
        
    
        const longestLabelLength = Math.max(...series.map(s => s.name.length));
        const additionalMargin = longestLabelLength * 4;
    
        const chart = Highcharts.chart('chart-container', {
            chart: { 
                type: 'line', 
                height: 'auto', 
                spacingRight: additionalMargin, 
                marginRight: additionalMargin 
            },
            title: { 
                text: 'Monthly natural gas demand (%) ', 
                align: 'left', 
                style: { fontWeight: 'bold',
                    fontSize: '20px'
                 }
            },
            subtitle: { 
                text: '2021 - 2025 indexed to 2019-2021 monthly average', 
                align: 'left', 
                style: { color: 'grey',
                    fontSize: '15px'
                 } 
            },
            yAxis: {
                title: { text: '%' },
                min: 0, // Ensure Y-axis always starts at 0
                plotLines: [{
                    value: 100, // Reference line at 100%
                    color: 'black',
                    width: 2, // Match "Fit for 55" and "REPowerEU" line width
                    zIndex: 2, // Ensure it's above other elements
                    dashStyle: "ShortDot", // Match target lines
                    label: { 
                        text: '100%', 
                        align: 'left',
                        x: -36, 
                        y: 3, 
                        style: {
                            color: 'black',
                            fontSize: '12px',
                            fontWeight: 'bold'
                        }
                    }
                }],
                
            },
            xAxis: {
                type: 'datetime',
                dateTimeLabelFormats: {
                    month: '%b %Y'
                },
                tickInterval: 3 * 30 * 24 * 60 * 60 * 1000, // 3 months in milliseconds
                min: Date.UTC(2019, 0, 1)
            },
            tooltip: {
                formatter: function() {
                    return `<b>${this.series.name}</b><br>${Highcharts.dateFormat('%b %Y', this.x)}: ${this.y.toFixed(2)} %`;
                }
            },
            plotOptions: {
                series: {
                    marker: { enabled: false } // Remove markers from all lines
                }
            },
            legend: {
                enabled: true, // Enable the Highcharts legend
                layout: 'horizontal', // Display at the bottom
                align: 'center',
                verticalAlign: 'bottom',
                itemStyle: {
                    fontWeight: 'bold',
                    fontSize: '12px'
                }
            },
            
            series,
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
                            'downloadPNG', // <<< ADD PNG DOWNLOAD BUTTON
                            'downloadCSV'
                        ]
                    }
                }
            },
            
            responsive: { 
                rules: [{ 
                    condition: { maxWidth: 500 }, 
                    chartOptions: { 
                        legend: { layout: 'horizontal', align: 'center', verticalAlign: 'bottom' } 
                    } 
                }] 
            }
        });
    
        reorderLegendItems(chart);
        if (pymChild) pymChild.sendHeight();
    }
    

    fetchData(createChart);
    initializePym();
});