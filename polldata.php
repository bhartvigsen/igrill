<?php

function dd($v) { die(var_dump($v)); }

$todaysLogs = file_get_contents('./logs/' .  date('y-m-d') . '.dat');
$todaysLogsSplit = explode("\n", $todaysLogs);
array_pop($todaysLogsSplit);

$processedRows = [];
foreach ($todaysLogsSplit as $row) {
	$currentRow = explode('|', $row);
	$unixTime = $currentRow[0];
	$temps = json_decode($currentRow[1]);
	$probe1 = ($temps->{"1"} !== false) ? (int) $temps->{"1"} : false;
	$probe2 = ($temps->{"2"} !== false) ? (int) $temps->{"2"} : false;
	$probe3 = ($temps->{"3"} !== false) ? (int) $temps->{"3"} : false;
	$probe4 = ($temps->{"4"} !== false) ? (int) $temps->{"4"} : false;
	$batteryLevel = (int) trim($currentRow[2]);
	$processedRows[] = [$unixTime, $batteryLevel, $probe1, $probe2, $probe3, $probe4];
}
$currentData = $processedRows[count($processedRows) - 1];
$return = new StdClass;
$return->currentData = $currentData;
$return->allData = $processedRows;
exit(json_encode($return));
