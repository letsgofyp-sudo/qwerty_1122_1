// ====== Dummy data: replace via AJAX calls to your Django REST endpoints ======

// KPIs
document.getElementById('kpi-active-users').textContent =  1_250;
document.getElementById('kpi-rides-today').textContent  =  340;
document.getElementById('kpi-cancellations').textContent =  27;
document.getElementById('kpi-wait-time').textContent    = '4m 18s';
document.getElementById('kpi-completed-trips').textContent = 313;
document.getElementById('kpi-flagged').textContent      =   5;

// 1) Time‑series: rides/day over past week
new Chart(document.getElementById('tsRidesChart'), {
  type: 'line',
  data: {
    labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    datasets: [{
      label: 'Rides Completed',
      data: [300, 320, 310, 340, 360, 380, 400],
      backgroundColor: 'rgba(46,204,113,0.2)',
      borderColor: '#27ae60',
      fill: true
    }]
  },
  options: {
    title: { display:true, text:'Daily Completed Rides' },
    responsive:true
  }
});

// 2) Heatmap‑style: request density by hour (using a bar‑gradient hack)
new Chart(document.getElementById('ridesByHourHeatmap'), {
  type: 'bar',
  data: {
    labels: ['0h','4h','8h','12h','16h','20h','24h'],
    datasets:[{
      label:'Ride Requests',
      data: [10, 50, 200, 350, 280, 120, 30],
      backgroundColor: function(ctx) {
        const v = ctx.dataset.data[ctx.dataIndex];
        return v>300 ? '#c0392b' : v>200 ? '#e67e22' : '#f1c40f';
      }
    }]
  },
  options: {
    title:{ display:true, text:'Request Density by Hour' },
    legend:{ display:false },
    responsive:true
  }
});

// 3) User Growth: active users by day (area + line dual‑axis)
new Chart(document.getElementById('userGrowthChart'), {
  type: 'line',
  data: {
    labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    datasets: [
      {
        label: 'Active Drivers',
        data: [800, 820, 830, 850, 870, 900, 920],
        backgroundColor: 'rgba(52,152,219,0.2)',
        borderColor: '#2980b9',
        fill: true
      },
      {
        label: 'Active Riders',
        data: [600, 620, 640, 660, 680, 700, 730],
        backgroundColor: 'rgba(155,89,182,0.2)',
        borderColor: '#9b59b6',
        fill: true
      }
    ]
  },
  options: {
    title:{ display:true, text:'Daily Active Users' },
    responsive:true
  }
});

// 4) Cancellation Reasons: doughnut
new Chart(document.getElementById('cancellationDoughnut'), {
  type:'doughnut',
  data:{
    labels:['User Cancel','No Driver','Safety','Other'],
    datasets:[{
      data:[12, 8, 5, 2],
      backgroundColor:['#e74c3c','#f39c12','#c0392b','#7f8c8d']
    }]
  },
  options:{
    title:{ display:true, text:'Cancellation Breakdown' },
    responsive:true
  }
});

// 5) Wait vs. Completed: dual‑axis bar+line
new Chart(document.getElementById('waitVsCompleted'), {
  type: 'bar',
  data: {
    labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    datasets: [
      {
        type:'bar',
        label:'Completed Trips',
        data:[300,320,310,340,360,380,400],
        backgroundColor:'#2ecc71',
        yAxisID:'y1'
      },
      {
        type:'line',
        label:'Avg Wait (min)',
        data:[5,4.8,4.9,4.6,4.4,4.3,4.2],
        borderColor:'#e67e22',
        fill:false,
        yAxisID:'y2'
      }
    ]
  },
  options:{
    title:{ display:true, text:'Trips vs. Avg. Wait Time' },
    responsive:true,
    scales:{
      yAxes:[
        { id:'y1', position:'left', ticks:{ beginAtZero:true }, scaleLabel:{ display:true, labelString:'Trips' } },
        { id:'y2', position:'right', ticks:{ beginAtZero:true }, scaleLabel:{ display:true, labelString:'Wait (min)' }, gridLines:{ drawOnChartArea:false } }
      ]
    }
  }
});
