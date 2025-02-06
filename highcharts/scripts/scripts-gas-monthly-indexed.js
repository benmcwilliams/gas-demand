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
        // Ensure the path to JSON file is correct for both local and embedded contexts
        jQuery.getJSON('data/monthly_demand_indexed.json', function(data) {
            const groupedData = groupDataByGroupValue(data);
            callback(groupedData);
        }).fail(function() {
            console.error("Error loading the JSON file.");
        });
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
    
        const $showAllButton = jQuery('<button id="show-all" class="toggle-button">').text('Show All').appendTo($legendContainer);
        const $hideAllButton = jQuery('<button id="hide-all" class="toggle-button">').text('Hide All').appendTo($legendContainer);
    
        $showAllButton.click(function() {
            chart.series.forEach(series => series.setVisible(true, false));
            chart.redraw();
            reorderLegendItems(chart);
        });
    
        $hideAllButton.click(function() {
            chart.series.forEach(series => series.setVisible(false, false));
            chart.redraw();
            reorderLegendItems(chart);
        });
    
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

    function createChart(data) {
        const series = Object.keys(data).map((groupValue, i) => ({
            name: groupValue,
            data: formatSeriesData(data[groupValue]),
            visible: groupValue === "Europe* - total",
            color: getColorFromCSS(cssColorVars[i]),
            marker: {
                symbol: 'circle',
                radius: 2.5,
                lineWidth: 1,
                lineColor: getColorFromCSS(cssColorVars[i]),
                fillColor: getColorFromCSS(cssColorVars[i])
            },
            dataLabels: {
                enabled: true,
                align: 'left',
                style: { fontWeight: 'bold', fontFamily: 'Roboto', textOutline: 'none', fontSize: '10px', color: getColorFromCSS(cssColorVars[i]) },
                formatter: function() {
                    return this.point.index === this.series.data.length - 1 ? this.series.name : null;
                },
                x: 10, y: 0, crop: false, overflow: 'allow', connectorColor: 'grey', connectorWidth: 1, allowOverlap: true
            }            
        }));

        const longestLabelLength = Math.max(...series.map(s => s.name.length));
        const additionalMargin = longestLabelLength * 4;

        const chart = Highcharts.chart('chart-container', {
            chart: { type: 'line', height: 'auto', spacingRight: additionalMargin, marginRight: additionalMargin },
            title: { text: 'Monthly natural gas demand (%) ', align: 'left', style: { fontWeight: 'bold' } },
            subtitle: { text: '2021 - 2025 indexed to 2019-2021 monthly average', align: 'left', style: {  color: 'grey' } },
            yAxis: {
                title: { text: '%' },
                plotLines: [{
                    value: 100, // The value where the line will appear
                    color: 'gray', // Line color
                    width: 1, // Line width
                    zIndex: 1, // Ensure it appears below the series
                    dashStyle: 'Dash', // Optional: make it dashed
                    label: { 
                        text: '100', // Label for the line
                        align: 'left', // Align the label to the left
                        x: -36, // Adjust the horizontal position (margin)
                        y: 3, // Fine-tune vertical alignment
                        style: {
                            color: 'black', // Label color
                            fontSize: '12px', // Optional: Adjust font size
                            fontWeight: 'bold'
                        }
                    }
                }]
            },
            
            xAxis: {
                type: 'datetime',
                dateTimeLabelFormats: {
                    month: '%b %Y'
                },
                tickInterval: 3 * 30 * 24 * 60 * 60 * 1000, // 3 months in milliseconds
                min: Date.UTC(2021, 11, 1)
            },
            tooltip: {
                formatter: function() {
                    // Hide tooltip for the first point
                    if (this.point.index === 0) {
                        return false; // No tooltip for the first point
                    }
            
                    // Tooltip for all other points
                    return `<b>${this.series.name}</b><br>${Highcharts.dateFormat('%b %Y', this.x)}: ${this.y.toFixed(2)} %`;
                }
            },
            
            plotOptions: {
                series: {
                    marker: { enabled: true, symbol: 'circle', lineWidth: 1 }
                }
            },
            legend: { enabled: false },
            series,
            exporting: {
                enabled: true,
                csv: {
                    itemDelimiter: ';', // Use semicolon as the field separator
                    lineDelimiter: '\n', // Optional: Newline for line breaks
                    decimalPoint: ',' // Use comma as the decimal separator
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
            },
            responsive: { rules: [{ condition: { maxWidth: 500 }, chartOptions: { legend: { layout: 'horizontal', align: 'center', verticalAlign: 'bottom' } } }] }
        });

        reorderLegendItems(chart);
        if (pymChild) pymChild.sendHeight();
    }

    fetchData(createChart);
    initializePym();
});
