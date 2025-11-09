// Common time intervals in milliseconds
const HOUR = 3600 * 1000;
const DAY = 24 * HOUR;
const WEEK = 7 * DAY;
const MONTH = 30 * DAY;
const YEAR = 365 * DAY;

chart = new Chart("chart", {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        label: "Humidity (%)",
        yAxisID: "A",
        fill: false,
        backgroundColor: "rgba(0,255,0,1)",
        borderColor: "rgba(0,255,0,1)",
        pointRadius: 0,
        data: [],
      },
      {
        label: "Temperature (F)",
        yAxisID: "A",
        fill: false,
        backgroundColor: "rgba(0,0,255,1)",
        borderColor: "rgba(0,0,255,1)",
        pointRadius: 0,
        data: [],
      },
      {
        label: "Power (W)",
        yAxisID: "B",
        fill: false,
        backgroundColor: "rgba(255,0,0,1)",
        borderColor: "rgba(255,0,0,1)",
        pointRadius: 0,
        data: [],
      },
    ],
  },
  options: {
    title: {
      display: true,
      text: "Loading...",
    },
    scales: {
      xAxes: [
        {
          type: "time",
          time: {
            unit: "hour",
          },
          display: true,
          scaleLabel: {
            display: true,
            labelString: "Date",
          },
        },
      ],
      yAxes: [
        {
          id: "A",
          type: "linear",
          position: "left",
          ticks: {
            max: 100,
            min: 0,
          },
        },
        {
          id: "B",
          type: "linear",
          position: "right",
          ticks: {
            max: 1000,
            min: 0,
          },
        },
      ],
    },
  },
});

function formatTime(rollup, iso_str) {
  const date = new Date(iso_str);

  switch (rollup) {
    // When using date/month rollup, leave it in UTC
    // This avoids confusion because the beginning of
    // the month is still in the previous month in local time
    case "day":
      return date.toLocaleDateString(undefined, { timeZone: "UTC" });

    case "month":
      // Format as "November 2025"
      return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        timeZone: "UTC",
      });

    default:
      return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  }
}

function drawChart() {
  startDate = new Date(endDate.getTime() - delta);
  fetch(dataUrl(rollup, startDate, endDate))
    .then((response) => response.json())
    .then((readings) => {
      const timeLabels = readings.map((d) => new Date(d[0]));
      const humidData = readings.map((d) => +d[1]);
      const tempData = readings.map((d) => +d[2]);
      const powerData = readings.map((d) => +d[3]);
      chart.data.labels = timeLabels;
      chart.data.datasets[0].data = humidData;
      chart.data.datasets[1].data = tempData;
      chart.data.datasets[2].data = powerData;
      chart.options.title.text =
        startDate.toLocaleString("en-US", dateFormat) +
        " - " +
        endDate.toLocaleString("en-US", dateFormat);
      chart.update();

      // Update the data table
      const tableBody = document.querySelector("#data tbody");
      tableBody.innerHTML = ""; // Clear the table body

      readings.reverse().forEach((reading) => {
        const row = document.createElement("tr");
        const [time, humid, temp, power] = reading;

        row.innerHTML = `
    <td>${formatTime(rollup, time)}</td>
    <td>${humid.toFixed(1)}</td>
    <td>${temp.toFixed(1)}</td>
    <td>${power.toFixed(0)}</td>
  `;

        tableBody.appendChild(row);
      });
    });
}

function dataUrl(rollup, start, end) {
  return (
    "/api/v1.0/measurements?rollup=" +
    rollup +
    "&start=" +
    start.toISOString() +
    "&end=" +
    end.toISOString()
  );
}

function setActiveMode(clickedElement) {
  const navContainer = clickedElement.closest(".chart-nav");
  const currentActive = navContainer.querySelector("a.active");
  if (currentActive) {
    currentActive.classList.remove("active");
  }
  clickedElement.classList.add("active");
}

function hourChart(btn) {
  setActiveMode(btn);
  rollup = "minute";
  delta = 60 * 60 * 1000;
  chart.options.scales.xAxes[0].time.unit = "minute";
  drawChart();
}

function dayChart(btn) {
  setActiveMode(btn);
  rollup = "hour";
  // Will not include current hour, so go back one extra
  delta = DAY + HOUR;
  chart.options.scales.xAxes[0].time.unit = "hour";
  drawChart();
}

function weekChart(btn) {
  setActiveMode(btn);
  rollup = "hour";
  delta = WEEK;
  chart.options.scales.xAxes[0].time.unit = "day";
  drawChart();
}

function monthChart(btn) {
  setActiveMode(btn);
  rollup = "day";
  // Will not include today, so go one extra day back
  delta = MONTH + DAY;
  chart.options.scales.xAxes[0].time.unit = "day";
  drawChart();
}

function yearChart(btn) {
  setActiveMode(btn);
  rollup = "month";
  delta = 365 * 86400 * 1000;
  chart.options.scales.xAxes[0].time.unit = "month";
  drawChart();
}

function earlier() {
  endDate.setTime(endDate.getTime() - delta);
  drawChart();
}

function later() {
  const now = new Date();

  endDate.setTime(endDate.getTime() + delta);
  if (endDate.getTime() > now.getTime()) {
    endDate = now;
  }

  drawChart();
}

function latest() {
  endDate = new Date();
  drawChart();
}

function loadLatest() {
  fetch("/api/v1.0/latest")
    .then((response) => response.json())
    .then((data) => {
      var d = new Date(data["time"]);
      if (Date.now() - d < 86400 * 1000) {
        document.getElementById("curhumid").innerText =
          data["humidity"].toFixed(1) + " %";
        document.getElementById("curtemp").innerText =
          data["temperature"].toFixed(0) + " \xB0";
        document.getElementById("curpower").innerText =
          data["power"].toFixed(0) + " W";
        document.getElementById("curtime").innerText = d.toLocaleString(
          "en-US",
          timeFormat,
        );
      }
    });
}

function loadAlarms() {
  const statusDict = {
    HEALTHY: ["&check;", "status-healthy"],
    UNHEALTHY: ["&cross;", "status-unhealthy"],
    UNKNOWN: ["&#63;", "status-unknown"],
  };

  fetch("/api/v1.0/alarms")
    .then((response) => response.json())
    .then((data) => {
      const tableBody = document.getElementById("alarms");
      tableBody.innerHTML = ""; // clear existing rows

      for (const alarm of data) {
        const [statusText, statusClass] = statusDict[alarm.state] || [
          "Unknown",
          "unknown",
        ];
        const row = document.createElement("tr");

        row.innerHTML = `
        <td>${alarm.message}</td>
        <td class="${statusClass}">${statusText}</td>
      `;

        tableBody.appendChild(row);
      }
    });
}

var timeFormat = { hour: "2-digit", minute: "2-digit", second: "2-digit" };
var dateFormat = { day: "2-digit", month: "2-digit", year: "2-digit" };
var endDate = new Date();
var startDate = new Date();
var delta = 86400 * 1000;
var rollup = "hour";

loadLatest();
loadAlarms();
dayChart(document.getElementById("day-mode"));
setInterval(loadLatest, 15 * 1000);
setInterval(loadAlarms, 60 * 1000);
