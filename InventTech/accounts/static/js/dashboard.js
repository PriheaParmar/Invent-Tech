(() => {
  // brand colors
  const BLUE = "rgba(28, 109, 216, 1)";
  const PINK = "rgba(238, 61, 133, 1)";
  const ORANGE = "rgba(250, 189, 100, 1)";

  // Trend chart (line)
  const trendEl = document.getElementById("trendChart");
  if (trendEl) {
    new Chart(trendEl, {
      type: "line",
      data: {
        labels: ["D-13","D-12","D-11","D-10","D-9","D-8","D-7","D-6","D-5","D-4","D-3","D-2","D-1","Today"],
        datasets: [
          {
            label: "Cutting",
            data: [2,3,2,4,3,5,4,6,5,6,7,6,8,9],
            borderColor: BLUE,
            tension: 0.35,
            fill: false
          },
          {
            label: "Stitching",
            data: [1,1,2,2,2,3,3,4,4,5,5,5,6,7],
            borderColor: PINK,
            tension: 0.35,
            fill: false
          },
          {
            label: "Finishing",
            data: [0,1,1,1,2,2,2,3,3,3,4,4,4,5],
            borderColor: ORANGE,
            tension: 0.35,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top" }
        },
        scales: {
          y: { beginAtZero: true }
        }
      }
    });
  }

  // Stock mix (doughnut)
  const mixEl = document.getElementById("mixChart");
  if (mixEl) {
    new Chart(mixEl, {
      type: "doughnut",
      data: {
        labels: ["Raw", "WIP", "Finished", "Accessories"],
        datasets: [{
          data: [48, 26, 18, 8],
          backgroundColor: [BLUE, PINK, ORANGE, "rgba(15, 23, 42, .15)"],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" }
        },
        cutout: "70%"
      }
    });
  }
})();

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("sbToggle");
  if (!btn) return;

  const saved = localStorage.getItem("inventtech_sidebar") || "open";
  if (saved === "collapsed") document.body.classList.add("sb-collapsed");

  btn.addEventListener("click", () => {
    document.body.classList.toggle("sb-collapsed");
    const collapsed = document.body.classList.contains("sb-collapsed");
    localStorage.setItem("inventtech_sidebar", collapsed ? "collapsed" : "open");
  });
});
