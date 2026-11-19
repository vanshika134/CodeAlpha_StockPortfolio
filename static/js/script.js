document.addEventListener("DOMContentLoaded", function () {

    // Update sample stock price when stock selection changes
    const stockSelect = document.getElementById("symbol");
    const pricePreview = document.getElementById("pricePreview");

    function updatePrice() {
        if (!stockSelect || !pricePreview) return;

        const selectedStock = window.portfolioData.prices[stockSelect.value];

        if (selectedStock) {
            pricePreview.textContent =
                "$" + Number(selectedStock.price).toFixed(2);
        }
    }

    if (stockSelect) {
        stockSelect.addEventListener("change", updatePrice);
        updatePrice();
    }


    // Portfolio allocation chart
    const chartCanvas = document.getElementById("allocationChart");
    const data = window.portfolioData;

    if (
        chartCanvas &&
        data &&
        data.labels.length > 0 &&
        typeof Chart !== "undefined"
    ) {
        new Chart(chartCanvas, {
            type: "doughnut",

            data: {
                labels: data.labels,

                datasets: [{
                    data: data.values,
                    borderWidth: 2,
                    borderColor: "#121a2d"
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        position: "right",

                        labels: {
                            color: "#aebbd1",
                            boxWidth: 10,
                            font: {
                                size: 10
                            }
                        }
                    }
                },

                cutout: "68%"
            }
        });
    }

});