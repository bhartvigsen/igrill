<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta http-equiv="X-UA-Compatible" content="IE=edge">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>iGrill Temps</title>
	<script src="jquery-3.1.1.min.js"></script>
	<script src="bootstrap.bundle.min.js"></script>
	<link href="bootstrap.min.css" rel="stylesheet">
</head>
<body>
<div class="container">
	<div class="row justify-content-center">
		<div class="col">
			<h1>Brian's Smoker Temperatures</h1>
			<div style="font-size: 18px" id="batteryLevel"></div>
			<table id="tempTable" class="table">
			</table>
		</div>
	</div>
<script>
var pollInterval = 5;
var lastTimestamp;

function pollData() {
	var form = new FormData();
	form.append('lastTimestamp', lastTimestamp);
	$.ajax({
		type: "POST",
		processData: false,
		contentType: false,
		url: "polldata.php",
		data: form,
		success: function(data) {
			data = JSON.parse(data);
			var probe1 = data.currentData[2]; if (probe1 === false) probe1 = 'Not Connected';
			var probe2 = data.currentData[3]; if (probe2 === false) probe2 = 'Not Connected';
			var probe3 = data.currentData[4]; if (probe3 === false) probe3 = 'Not Connected';
			var probe4 = data.currentData[5]; if (probe4 === false) probe4 = 'Not Connected';
			$('#tempTable').html([
				'<tr><td>Probe 1</td><td>' + probe1 + '</td></tr>',
				'<tr><td>Probe 1</td><td>' + probe2 + '</td></tr>',
				'<tr><td>Probe 1</td><td>' + probe3 + '</td></tr>',
				'<tr><td>Probe 1</td><td>' + probe4 + '</td></tr>'
			].join(' '));
			$('#batteryLevel').text('Battery level: ' + data.currentData[1]);
			console.log(data);
			poller = setTimeout(function() {
				pollData();
			}, pollInterval * 1000);
		},
		error: function(data) {
			poller = setTimeout(function() {
				pollData();
			}, pollInterval * 1000);
		}
	});
}
pollData();
</script>
</body>
