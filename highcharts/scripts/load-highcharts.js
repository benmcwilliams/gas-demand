/**
 * Single place to bump the Highcharts version for all highcharts/*.html pages.
 * HTML must set data-highcharts-bundle: "core" (Highcharts.Chart) or "stock" (stockChart).
 */
(function () {
    var HIGHCHARTS_VERSION = '11.4.8';
    var BASE = 'https://cdn.jsdelivr.net/npm/highcharts@' + HIGHCHARTS_VERSION;
    var bundle =
        (document.currentScript && document.currentScript.getAttribute('data-highcharts-bundle')) ||
        'core';
    var urls =
        bundle === 'stock'
            ? [
                  BASE + '/highstock.js',
                  BASE + '/modules/exporting.js',
                  BASE + '/modules/export-data.js',
                  BASE + '/modules/accessibility.js',
                  BASE + '/modules/offline-exporting.js',
              ]
            : [
                  BASE + '/highcharts.js',
                  BASE + '/modules/exporting.js',
                  BASE + '/modules/export-data.js',
              ];

    function loadSequential(i) {
        if (i >= urls.length) {
            window.dispatchEvent(new Event('highcharts:ready'));
            return;
        }
        var s = document.createElement('script');
        s.src = urls[i];
        s.onload = function () {
            loadSequential(i + 1);
        };
        s.onerror = function () {
            console.error('Highcharts script failed to load:', urls[i]);
        };
        document.head.appendChild(s);
    }
    loadSequential(0);
})();
