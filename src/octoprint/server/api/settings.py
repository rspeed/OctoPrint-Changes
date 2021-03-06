# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

from flask import request, jsonify

from octoprint.events import eventManager, Events
from octoprint.settings import settings
from octoprint.printer import getConnectionOptions

from octoprint.server import admin_permission
from octoprint.server.api import api
from octoprint.server.util.flask import restricted_access

import octoprint.plugin


#~~ settings


@api.route("/settings", methods=["GET"])
def getSettings():
	s = settings()

	connectionOptions = getConnectionOptions()

	data = {
		"api": {
			"enabled": s.getBoolean(["api", "enabled"]),
			"key": s.get(["api", "key"]) if admin_permission.can() else "n/a",
			"allowCrossOrigin": s.get(["api", "allowCrossOrigin"])
		},
		"appearance": {
			"name": s.get(["appearance", "name"]),
			"color": s.get(["appearance", "color"])
		},
		"printer": {
			"defaultExtrusionLength": s.getInt(["printerParameters", "defaultExtrusionLength"])
		},
		"webcam": {
			"streamUrl": s.get(["webcam", "stream"]),
			"snapshotUrl": s.get(["webcam", "snapshot"]),
			"ffmpegPath": s.get(["webcam", "ffmpeg"]),
			"bitrate": s.get(["webcam", "bitrate"]),
			"watermark": s.getBoolean(["webcam", "watermark"]),
			"flipH": s.getBoolean(["webcam", "flipH"]),
			"flipV": s.getBoolean(["webcam", "flipV"])
		},
		"feature": {
			"gcodeViewer": s.getBoolean(["gcodeViewer", "enabled"]),
			"temperatureGraph": s.getBoolean(["feature", "temperatureGraph"]),
			"waitForStart": s.getBoolean(["feature", "waitForStartOnConnect"]),
			"alwaysSendChecksum": s.getBoolean(["feature", "alwaysSendChecksum"]),
			"sdSupport": s.getBoolean(["feature", "sdSupport"]),
			"sdAlwaysAvailable": s.getBoolean(["feature", "sdAlwaysAvailable"]),
			"swallowOkAfterResend": s.getBoolean(["feature", "swallowOkAfterResend"]),
			"repetierTargetTemp": s.getBoolean(["feature", "repetierTargetTemp"])
		},
		"serial": {
			"port": connectionOptions["portPreference"],
			"baudrate": connectionOptions["baudratePreference"],
			"portOptions": connectionOptions["ports"],
			"baudrateOptions": connectionOptions["baudrates"],
			"autoconnect": s.getBoolean(["serial", "autoconnect"]),
			"timeoutConnection": s.getFloat(["serial", "timeout", "connection"]),
			"timeoutDetection": s.getFloat(["serial", "timeout", "detection"]),
			"timeoutCommunication": s.getFloat(["serial", "timeout", "communication"]),
			"timeoutTemperature": s.getFloat(["serial", "timeout", "temperature"]),
			"timeoutSdStatus": s.getFloat(["serial", "timeout", "sdStatus"]),
			"log": s.getBoolean(["serial", "log"])
		},
		"folder": {
			"uploads": s.getBaseFolder("uploads"),
			"timelapse": s.getBaseFolder("timelapse"),
			"timelapseTmp": s.getBaseFolder("timelapse_tmp"),
			"logs": s.getBaseFolder("logs"),
			"watched": s.getBaseFolder("watched")
		},
		"temperature": {
			"profiles": s.get(["temperature", "profiles"])
		},
		"system": {
			"actions": s.get(["system", "actions"]),
			"events": s.get(["system", "events"])
		},
		"terminalFilters": s.get(["terminalFilters"]),
		"cura": {
			"enabled": s.getBoolean(["cura", "enabled"]),
			"path": s.get(["cura", "path"]),
			"config": s.get(["cura", "config"])
		}
	}

	def process_plugin_result(name, plugin, result):
		if result:
			if not "plugins" in data:
				data["plugins"] = dict()
			if "__enabled" in result:
				del result["__enabled"]
			data["plugins"][name] = result

	octoprint.plugin.call_plugin(octoprint.plugin.SettingsPlugin,
	                             "on_settings_load",
	                             callback=process_plugin_result)

	return jsonify(data)


@api.route("/settings", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def setSettings():
	if "application/json" in request.headers["Content-Type"]:
		data = request.json
		s = settings()

		if "api" in data.keys():
			if "enabled" in data["api"].keys(): s.setBoolean(["api", "enabled"], data["api"]["enabled"])
			if "key" in data["api"].keys(): s.set(["api", "key"], data["api"]["key"], True)
			if "allowCrossOrigin" in data["api"].keys(): s.setBoolean(["api", "allowCrossOrigin"], data["api"]["allowCrossOrigin"])

		if "appearance" in data.keys():
			if "name" in data["appearance"].keys(): s.set(["appearance", "name"], data["appearance"]["name"])
			if "color" in data["appearance"].keys(): s.set(["appearance", "color"], data["appearance"]["color"])

		if "printer" in data.keys():
			if "defaultExtrusionLength" in data["printer"]: s.setInt(["printerParameters", "defaultExtrusionLength"], data["printer"]["defaultExtrusionLength"])

		if "webcam" in data.keys():
			if "streamUrl" in data["webcam"].keys(): s.set(["webcam", "stream"], data["webcam"]["streamUrl"])
			if "snapshotUrl" in data["webcam"].keys(): s.set(["webcam", "snapshot"], data["webcam"]["snapshotUrl"])
			if "ffmpegPath" in data["webcam"].keys(): s.set(["webcam", "ffmpeg"], data["webcam"]["ffmpegPath"])
			if "bitrate" in data["webcam"].keys(): s.set(["webcam", "bitrate"], data["webcam"]["bitrate"])
			if "watermark" in data["webcam"].keys(): s.setBoolean(["webcam", "watermark"], data["webcam"]["watermark"])
			if "flipH" in data["webcam"].keys(): s.setBoolean(["webcam", "flipH"], data["webcam"]["flipH"])
			if "flipV" in data["webcam"].keys(): s.setBoolean(["webcam", "flipV"], data["webcam"]["flipV"])

		if "feature" in data.keys():
			if "gcodeViewer" in data["feature"].keys(): s.setBoolean(["gcodeViewer", "enabled"], data["feature"]["gcodeViewer"])
			if "temperatureGraph" in data["feature"].keys(): s.setBoolean(["feature", "temperatureGraph"], data["feature"]["temperatureGraph"])
			if "waitForStart" in data["feature"].keys(): s.setBoolean(["feature", "waitForStartOnConnect"], data["feature"]["waitForStart"])
			if "alwaysSendChecksum" in data["feature"].keys(): s.setBoolean(["feature", "alwaysSendChecksum"], data["feature"]["alwaysSendChecksum"])
			if "sdSupport" in data["feature"].keys(): s.setBoolean(["feature", "sdSupport"], data["feature"]["sdSupport"])
			if "sdAlwaysAvailable" in data["feature"].keys(): s.setBoolean(["feature", "sdAlwaysAvailable"], data["feature"]["sdAlwaysAvailable"])
			if "swallowOkAfterResend" in data["feature"].keys(): s.setBoolean(["feature", "swallowOkAfterResend"], data["feature"]["swallowOkAfterResend"])
			if "repetierTargetTemp" in data["feature"].keys(): s.setBoolean(["feature", "repetierTargetTemp"], data["feature"]["repetierTargetTemp"])

		if "serial" in data.keys():
			if "autoconnect" in data["serial"].keys(): s.setBoolean(["serial", "autoconnect"], data["serial"]["autoconnect"])
			if "port" in data["serial"].keys(): s.set(["serial", "port"], data["serial"]["port"])
			if "baudrate" in data["serial"].keys(): s.setInt(["serial", "baudrate"], data["serial"]["baudrate"])
			if "timeoutConnection" in data["serial"].keys(): s.setFloat(["serial", "timeout", "connection"], data["serial"]["timeoutConnection"])
			if "timeoutDetection" in data["serial"].keys(): s.setFloat(["serial", "timeout", "detection"], data["serial"]["timeoutDetection"])
			if "timeoutCommunication" in data["serial"].keys(): s.setFloat(["serial", "timeout", "communication"], data["serial"]["timeoutCommunication"])
			if "timeoutTemperature" in data["serial"].keys(): s.setFloat(["serial", "timeout", "temperature"], data["serial"]["timeoutTemperature"])
			if "timeoutSdStatus" in data["serial"].keys(): s.setFloat(["serial", "timeout", "sdStatus"], data["serial"]["timeoutSdStatus"])

			oldLog = s.getBoolean(["serial", "log"])
			if "log" in data["serial"].keys(): s.setBoolean(["serial", "log"], data["serial"]["log"])
			if oldLog and not s.getBoolean(["serial", "log"]):
				# disable debug logging to serial.log
				logging.getLogger("SERIAL").debug("Disabling serial logging")
				logging.getLogger("SERIAL").setLevel(logging.CRITICAL)
			elif not oldLog and s.getBoolean(["serial", "log"]):
				# enable debug logging to serial.log
				logging.getLogger("SERIAL").setLevel(logging.DEBUG)
				logging.getLogger("SERIAL").debug("Enabling serial logging")

		if "folder" in data.keys():
			if "uploads" in data["folder"].keys(): s.setBaseFolder("uploads", data["folder"]["uploads"])
			if "timelapse" in data["folder"].keys(): s.setBaseFolder("timelapse", data["folder"]["timelapse"])
			if "timelapseTmp" in data["folder"].keys(): s.setBaseFolder("timelapse_tmp", data["folder"]["timelapseTmp"])
			if "logs" in data["folder"].keys(): s.setBaseFolder("logs", data["folder"]["logs"])
			if "watched" in data["folder"].keys(): s.setBaseFolder("watched", data["folder"]["watched"])

		if "temperature" in data.keys():
			if "profiles" in data["temperature"].keys(): s.set(["temperature", "profiles"], data["temperature"]["profiles"])

		if "terminalFilters" in data.keys():
			s.set(["terminalFilters"], data["terminalFilters"])

		if "system" in data.keys():
			if "actions" in data["system"].keys(): s.set(["system", "actions"], data["system"]["actions"])
			if "events" in data["system"].keys(): s.set(["system", "events"], data["system"]["events"])

		cura = data.get("cura", None)
		if cura:
			path = cura.get("path")
			if path:
				s.set(["cura", "path"], path)

			config = cura.get("config")
			if config:
				s.set(["cura", "config"], config)

			# Enabled is a boolean so we cannot check that we have a result
			enabled = cura.get("enabled")
			s.setBoolean(["cura", "enabled"], enabled)

		if "plugins" in data:
			for name, plugin in octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.SettingsPlugin).items():
				if name in data["plugins"]:
					plugin.on_settings_save(data["plugins"][name])


		if s.save():
			eventManager().fire(Events.SETTINGS_UPDATED)

	return getSettings()

