// Chart.js Configuration and Utilities
class ChartManager {
    constructor() {
        this.defaultColors = {
            primary: '#3498db',
            secondary: '#2ecc71',
            success: '#27ae60',
            danger: '#e74c3c',
            warning: '#f39c12',
            info: '#17a2b8',
            light: '#ecf0f1',
            dark: '#2c3e50'
        };
        
        this.chartInstances = {};
        this.setupChartDefaults();
    }
    
    setupChartDefaults() {
        // Register Chart.js plugins
        Chart.register({
            id: 'customBackground',
            beforeDraw: (chart) => {
                if (chart.options.plugins?.customBackground?.color) {
                    const ctx = chart.ctx;
                    ctx.save();
                    ctx.globalCompositeOperation = 'destination-over';
                    ctx.fillStyle = chart.options.plugins.customBackground.color;
                    ctx.fillRect(0, 0, chart.width, chart.height);
                    ctx.restore();
                }
            }
        });
        
        // Global chart defaults
        Chart.defaults.font.family = "'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif";
        Chart.defaults.color = '#6c757d';
        Chart.defaults.borderColor = 'rgba(0, 0, 0, 0.1)';
        
        // Animation defaults
        Chart.defaults.animation.duration = 1000;
        Chart.defaults.animation.easing = 'easeOutQuart';
    }
    
    createChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas element #${canvasId} not found`);
            return null;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.chartInstances[canvasId]) {
            this.chartInstances[canvasId].destroy();
        }
        
        // Create new chart
        const chart = new Chart(ctx, config);
        this.chartInstances[canvasId] = chart;
        
        return chart;
    }
    
    createSalesChart(canvasId, data) {
        return this.createChart(canvasId, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Sales Revenue',
                    data: data.values,
                    borderColor: this.defaultColors.primary,
                    backgroundColor: this.hexToRgba(this.defaultColors.primary, 0.1),
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: this.defaultColors.primary,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.7)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += 'KES ' + context.parsed.y.toLocaleString('en-KE', {
                                    minimumFractionDigits: 2
                                });
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return 'KES ' + value.toLocaleString();
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'nearest'
                },
                elements: {
                    line: {
                        tension: 0.4
                    }
                }
            }
        });
    }
    
    createBarChart(canvasId, data) {
        return this.createChart(canvasId, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((dataset, index) => ({
                    label: dataset.label,
                    data: dataset.values,
                    backgroundColor: this.getColorPalette()[index % this.getColorPalette().length],
                    borderColor: this.getColorPalette()[index % this.getColorPalette().length],
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: data.datasets.length > 1,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                }
            }
        });
    }
    
    createPieChart(canvasId, data) {
        return this.createChart(canvasId, {
            type: 'pie',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: this.getColorPalette(),
                    borderColor: '#fff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    createDoughnutChart(canvasId, data) {
        return this.createChart(canvasId, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: this.getColorPalette(),
                    borderColor: '#fff',
                    borderWidth: 2,
                    cutout: '70%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }
    
    createStackedBarChart(canvasId, data) {
        return this.createChart(canvasId, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((dataset, index) => ({
                    label: dataset.label,
                    data: dataset.values,
                    backgroundColor: this.getColorPalette()[index % this.getColorPalette().length],
                    borderColor: this.getColorPalette()[index % this.getColorPalette().length],
                    borderWidth: 1
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    }
    
    createRadarChart(canvasId, data) {
        return this.createChart(canvasId, {
            type: 'radar',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((dataset, index) => ({
                    label: dataset.label,
                    data: dataset.values,
                    backgroundColor: this.hexToRgba(this.getColorPalette()[index], 0.2),
                    borderColor: this.getColorPalette()[index],
                    borderWidth: 2,
                    pointBackgroundColor: this.getColorPalette()[index],
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        ticks: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                elements: {
                    line: {
                        tension: 0
                    }
                }
            }
        });
    }
    
    createHorizontalBarChart(canvasId, data) {
        return this.createChart(canvasId, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: data.label || 'Values',
                    data: data.values,
                    backgroundColor: data.values.map((value, index) => {
                        const colors = this.getColorPalette();
                        return colors[index % colors.length];
                    }),
                    borderColor: data.values.map((value, index) => {
                        const colors = this.getColorPalette();
                        return colors[index % colors.length];
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    
    createMixedChart(canvasId, data) {
        return this.createChart(canvasId, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        type: 'bar',
                        label: data.barLabel || 'Bar Data',
                        data: data.barValues,
                        backgroundColor: this.hexToRgba(this.defaultColors.primary, 0.7),
                        borderColor: this.defaultColors.primary,
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        type: 'line',
                        label: data.lineLabel || 'Line Data',
                        data: data.lineValues,
                        borderColor: this.defaultColors.success,
                        backgroundColor: this.hexToRgba(this.defaultColors.success, 0.1),
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: data.barLabel || 'Bar Data'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: data.lineLabel || 'Line Data'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    }
    
    // Utility methods
    getColorPalette() {
        return [
            '#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6',
            '#1abc9c', '#d35400', '#c0392b', '#16a085', '#8e44ad',
            '#27ae60', '#2980b9', '#f1c40f', '#e67e22', '#95a5a6'
        ];
    }
    
    hexToRgba(hex, alpha = 1) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    
    updateChartData(chartId, newData) {
        const chart = this.chartInstances[chartId];
        if (!chart) {
            console.error(`Chart ${chartId} not found`);
            return;
        }
        
        chart.data.labels = newData.labels || chart.data.labels;
        
        if (Array.isArray(newData.datasets)) {
            chart.data.datasets = newData.datasets;
        } else if (newData.values) {
            chart.data.datasets[0].data = newData.values;
        }
        
        chart.update();
    }
    
    updateChartOptions(chartId, newOptions) {
        const chart = this.chartInstances[chartId];
        if (!chart) {
            console.error(`Chart ${chartId} not found`);
            return;
        }
        
        Object.assign(chart.options, newOptions);
        chart.update();
    }
    
    destroyChart(chartId) {
        const chart = this.chartInstances[chartId];
        if (chart) {
            chart.destroy();
            delete this.chartInstances[chartId];
        }
    }
    
    destroyAllCharts() {
        Object.keys(this.chartInstances).forEach(chartId => {
            this.destroyChart(chartId);
        });
    }
    
    exportChart(chartId, format = 'png') {
        const chart = this.chartInstances[chartId];
        if (!chart) {
            console.error(`Chart ${chartId} not found`);
            return null;
        }
        
        const canvas = chart.canvas;
        
        switch(format) {
            case 'png':
                return canvas.toDataURL('image/png');
            case 'jpg':
                return canvas.toDataURL('image/jpeg', 0.9);
            case 'svg':
                // For SVG export, we need to use a different approach
                const serializer = new XMLSerializer();
                const source = serializer.serializeToString(canvas);
                return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(source);
            default:
                return canvas.toDataURL();
        }
    }
    
    downloadChart(chartId, filename = 'chart', format = 'png') {
        const dataUrl = this.exportChart(chartId, format);
        if (!dataUrl) return;
        
        const link = document.createElement('a');
        link.download = `${filename}.${format}`;
        link.href = dataUrl;
        link.click();
    }
    
    // Theme management
    applyDarkTheme(chartId) {
        const chart = this.chartInstances[chartId];
        if (!chart) return;
        
        const darkOptions = {
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            }
        };
        
        this.updateChartOptions(chartId, darkOptions);
    }
    
    applyLightTheme(chartId) {
        const chart = this.chartInstances[chartId];
        if (!chart) return;
        
        const lightOptions = {
            scales: {
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(0, 0, 0, 0.7)'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(0, 0, 0, 0.7)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgba(0, 0, 0, 0.7)'
                    }
                }
            }
        };
        
        this.updateChartOptions(chartId, lightOptions);
    }
    
    // Animation controls
    animateChart(chartId) {
        const chart = this.chartInstances[chartId];
        if (!chart) return;
        
        chart.data.datasets.forEach((dataset, i) => {
            dataset.backgroundColor = this.getColorPalette()[i % this.getColorPalette().length];
        });
        
        chart.update('active');
    }
    
    resetAnimation(chartId) {
        const chart = this.chartInstances[chartId];
        if (!chart) return;
        
        chart.reset();
    }
}

// Initialize ChartManager globally
window.ChartManager = new ChartManager();

// Helper function to format currency in tooltips
Chart.register({
    id: 'currencyFormatter',
    beforeTooltipDraw: function(chart) {
        // Custom currency formatting if needed
    }
});

// Auto-initialize charts with data attributes
document.addEventListener('DOMContentLoaded', function() {
    // Find all canvas elements with data-chart attribute
    document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
        const chartType = canvas.getAttribute('data-chart');
        const chartData = JSON.parse(canvas.getAttribute('data-chart-data') || '{}');
        
        if (chartType && chartData) {
            switch(chartType) {
                case 'line':
                    window.ChartManager.createSalesChart(canvas.id, chartData);
                    break;
                case 'bar':
                    window.ChartManager.createBarChart(canvas.id, chartData);
                    break;
                case 'pie':
                    window.ChartManager.createPieChart(canvas.id, chartData);
                    break;
                case 'doughnut':
                    window.ChartManager.createDoughnutChart(canvas.id, chartData);
                    break;
                case 'radar':
                    window.ChartManager.createRadarChart(canvas.id, chartData);
                    break;
            }
        }
    });
});