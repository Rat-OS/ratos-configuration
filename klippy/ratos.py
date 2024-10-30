import os, logging, re, glob
import logging, collections, pathlib, subprocess
from . import bed_mesh as BedMesh

#####
# RatOS
#####

PRUSA_SLICER = "prusaslicer"
SUPER_SLICER = "superslicer"
ORCA_SLICER = "orcaslicer"
UNKNOWN_SLICER = "unknown"

REMOVED_BY_POST_PROCESSOR = "; Removed by RatOS post processor: "

class RatOS:

	#####
	# Initialize
	#####
	def __init__(self, config):
		self.config = config
		self.printer = config.get_printer()
		self.name = config.get_name()
		self.gcode = self.printer.lookup_object('gcode')
		self.reactor = self.printer.get_reactor()

		self.old_is_graph_files = []
		self.contact_mesh = None
		self.pmgr = BedMeshProfileManager(self.config, self)

		self.load_settings()
		self.register_commands()
		self.register_handler()

	#####
	# Handler
	#####
	def register_handler(self):
		self.printer.register_event_handler("klippy:connect", self._connect)

	def _connect(self):
		self.v_sd = self.printer.lookup_object('virtual_sdcard', None)
		self.sdcard_dirname = self.v_sd.sdcard_dirname
		self.bed_mesh = self.printer.lookup_object('bed_mesh')
		self.dual_carriage = None
		if self.config.has_section("dual_carriage"):
			self.dual_carriage = self.printer.lookup_object("dual_carriage", None)
		self.rmmu_hub = None
		if self.config.has_section("rmmu_hub"):
			self.rmmu_hub = self.printer.lookup_object("rmmu_hub", None)

	#####
	# Settings
	#####
	def load_settings(self):
		self.enable_post_processing = True if self.config.get('enable_post_processing', "false").lower() == "true" else False 
		
	def get_status(self, eventtime):
		return {'name': self.name}

	#####
	# Gcode commands
	#####
	def register_commands(self):
		self.gcode.register_command('HELLO_RATOS', self.cmd_HELLO_RATOS, desc=(self.desc_HELLO_RATOS))
		self.gcode.register_command('CACHE_IS_GRAPH_FILES', self.cmd_CACHE_IS_GRAPH_FILES, desc=(self.desc_CACHE_IS_GRAPH_FILES))
		self.gcode.register_command('SHOW_IS_GRAPH_FILES', self.cmd_SHOW_IS_GRAPH_FILES, desc=(self.desc_SHOW_IS_GRAPH_FILES))
		self.gcode.register_command('CONSOLE_ECHO', self.cmd_CONSOLE_ECHO, desc=(self.desc_CONSOLE_ECHO))
		self.gcode.register_command('RATOS_LOG', self.cmd_RATOS_LOG, desc=(self.desc_RATOS_LOG))
		self.gcode.register_command('PROCESS_GCODE_FILE', self.cmd_PROCESS_GCODE_FILE, desc=(self.desc_PROCESS_GCODE_FILE))
		self.gcode.register_command('BEACON_APPLY_SCAN_COMPENSATION', self.cmd_BEACON_APPLY_SCAN_COMPENSATION, desc=(self.desc_BEACON_APPLY_SCAN_COMPENSATION))
		self.gcode.register_command('TEST_PROCESS_GCODE_FILE', self.cmd_TEST_PROCESS_GCODE_FILE, desc=(self.desc_TEST_PROCESS_GCODE_FILE))

	desc_TEST_PROCESS_GCODE_FILE = "Test the G-code post processor for IDEX and RMMU, onyl for debugging purposes"
	def cmd_TEST_PROCESS_GCODE_FILE(self, gcmd):
		dual_carriage = self.dual_carriage
		self.dual_carriage = True
		filename = gcmd.get('FILENAME', "")
		if filename[0] == '/':
			filename = filename[1:]
		self.process_gode_file(filename, True)
		self.dual_carriage = dual_carriage

	desc_HELLO_RATOS = "RatOS mainsail welcome message"
	def cmd_HELLO_RATOS(self, gcmd):
		url = "https://os.ratrig.com/"
		img = "../server/files/config/RatOS/Logo-white.png"
		ratos_version = self.get_ratos_version().split('-')
		_title = '<b><p style="font-weight-bold; margin:0; margin-bottom:0px; color:white">Welcome to RatOS ' +  ratos_version[0] + '</p></b>'
		_sub_title = '-'.join(ratos_version)
		_info = '\nClick image to open documentation.'
		_img = '\n<a href="' + url + '" target="_blank" ><img style="margin-top:6px;" src="' + img + '" width="258px"></a>'
		self.gcode.respond_raw(_title + _sub_title + _img + _info)

	desc_CONSOLE_ECHO = "Multiline console output"
	def cmd_CONSOLE_ECHO(self, gcmd):
		title = gcmd.get('TITLE', '')
		msg = gcmd.get('MSG', '')
		type = gcmd.get('TYPE', '')

		color = "white" 
		opacity = 1.0
		if type == 'info': color = "#38bdf8" 
		if type == 'success': color = "#a3e635" 
		if type == 'warning': color = "#fbbf24" 
		if type == 'alert': color = "#f87171" 
		if type == 'debug': color = "#38bdf8" 
		if type == 'debug': opacity = 0.7 

		_title = '<b><p style="font-weight-bold; margin:0; opacity:' + str(opacity) + '; color:' + color + '">' + title + '</p></b>'
		_msg = '<p style="margin:0; opacity:' + str(opacity) + '; color:' + color + '">' + msg.replace("_N_","\n") + '</p>'

		self.gcode.respond_raw(_title + _msg)

	desc_SHOW_IS_GRAPH_FILES = "Shows the last generated IS graph in the console"
	def cmd_SHOW_IS_GRAPH_FILES(self, gcmd):
		title = gcmd.get('TITLE', '')
		try:
			counter = 0
			new_is_graph_files = self.get_is_graph_files()
			for file_path in new_is_graph_files:
				if file_path not in self.old_is_graph_files:
					file_name = file_path.replace("/home/pi/printer_data/config/input_shaper/", "")
					url = file_path.replace("/home/pi/printer_data", "../server/files")
					title = title + ': ' if title != '' else ''
					_title = '<b><p style="font-weight-bold; margin:0; color:white">' + title + file_name + '</p></b>'
					_link = 'Click image to download or right click for options.'
					_img = '<a href="' + url + '" target="_blank" ><img src="' + url + '" width="100%"></a>'
					self.gcode.respond_raw(_title + _link + _img)
					counter += 1
					if counter == 10:
						break
			self.old_is_graph_files = []
		except Exception as exc:
			self.debug_echo("SHOW_IS_GRAPH_FILES", "Something went wrong. " + str(exc))

	desc_CACHE_IS_GRAPH_FILES = "Caches the current is graph files"
	def cmd_CACHE_IS_GRAPH_FILES(self, gcmd):
		self.old_is_graph_files = self.get_is_graph_files()

	desc_RATOS_LOG = "G-code logging command "
	def cmd_RATOS_LOG(self, gcmd):
		prefix = gcmd.get('PREFIX')
		msg = gcmd.get('MSG')
		logging.info(prefix + ": " + msg)

	desc_PROCESS_GCODE_FILE = "G-code post processor for IDEX and RMMU"
	def cmd_PROCESS_GCODE_FILE(self, gcmd):
		filename = gcmd.get('FILENAME', "")
		if filename[0] == '/':
			filename = filename[1:]
		if (self.dual_carriage == None and self.rmmu_hub == None) or not self.enable_post_processing:
			self.gcode.run_script_from_command("SET_GCODE_VARIABLE MACRO=START_PRINT VARIABLE=first_x VALUE=" + str(-1))
			self.gcode.run_script_from_command("SET_GCODE_VARIABLE MACRO=START_PRINT VARIABLE=first_y VALUE=" + str(-1))
			self.process_gode_file(filename, False)
			self.v_sd.cmd_SDCARD_PRINT_FILE(gcmd)
		else:
			if self.process_gode_file(filename, True):
				self.v_sd.cmd_SDCARD_PRINT_FILE(gcmd)
			else:
				raise self.printer.command_error("Could not process gcode file")

	desc_BEACON_APPLY_SCAN_COMPENSATION = "Compensates magnetic inaccuracies for beacon scan meshes."
	def cmd_BEACON_APPLY_SCAN_COMPENSATION(self, gcmd):
		profile = gcmd.get('PROFILE', "Contact")
		if not profile.strip():
			raise gcmd.error("Value for parameter 'PROFILE' must be specified")
		if profile not in self.pmgr.get_profiles():
			raise self.printer.command_error("Profile " + str(profile) + " not found for Beacon scan compensation")
		self.contact_mesh = self.pmgr.load_profile(profile)
		if not self.contact_mesh:
			raise self.printer.command_error("Could not load profile " + str(profile) + " for Beacon scan compensation")
		self.compensate_beacon_scan(profile)

	#####
	# Beacon Scan Compensation
	#####
	def compensate_beacon_scan(self, profile):
		systime = self.reactor.monotonic()
		try:
			if self.bed_mesh.z_mesh:
				profile_name = self.bed_mesh.z_mesh.get_profile_name()
				if profile_name != profile:
					points = self.bed_mesh.get_status(systime)["profiles"][profile_name]["points"]
					params = self.bed_mesh.z_mesh.get_mesh_params()
					x_step = ((params["max_x"] - params["min_x"]) / (len(points[0]) - 1))
					y_step = ((params["max_y"] - params["min_y"]) / (len(points) - 1))
					new_points = []
					for y in range(len(points)):
						new_points.append([])
						for x in range(len(points[0])):
							x_pos = params["min_x"] + x * x_step
							y_pos = params["min_y"] + y * y_step
							z_val = points[y][x]
							contact_z = self.contact_mesh.calc_z(x_pos, y_pos)
							new_z = z_val - (z_val - contact_z)
							new_points[y].append(new_z)
					self.bed_mesh.z_mesh.build_mesh(new_points)
					self.bed_mesh.save_profile(profile_name)
					self.bed_mesh.set_mesh(self.bed_mesh.z_mesh)
					self.gcode.run_script_from_command("CONSOLE_ECHO TYPE=debug TITLE='Beacon scan compensation' MSG='Mesh scan profile " + str(profile_name) + " compensated with contact profile " + str(profile) + "'")
		except BedMesh.BedMeshError as e:
			self.gcode.run_script_from_command("CONSOLE_ECHO TYPE=error TITLE='Beacon scan compensation error' MSG='" + str(e) + "'")

	#####
	# G-code post processor
	#####
	def process_gode_file(self, filename, enable_post_processing):
		echo_prefix = "POST_PROCESSOR"
		try:
			[path, size] = self.get_gcode_file_info(filename)
			meminfo = dict((i.split()[0].rstrip(':'),int(i.split()[1])) for i in open('/proc/meminfo').readlines())
			# check if file is too large for post processing, using a safety margin of 15%
			mem_available = meminfo['MemAvailable'] * 1024 * 0.85
			if (size > mem_available):
				if (enable_post_processing):
					raise self.printer.command_error("File is too large (file is %smb but only %smb of memory is available) for required IDEX post processing. A new post processor is coming soon without this limitation." % (size / 1024 / 1024, mem_available / 1024 / 1024))
				else:
					self.ratos_echo(echo_prefix, "File is too large for post processing (file is %smb but only %smb of memory is available), skipping.." % (size / 1024 / 1024, mem_available / 1024 / 1024))
					return True
			lines = self.get_gcode_file_lines(path)

			if (enable_post_processing):
				if self.gcode_already_processed(path):
					return True

			if (enable_post_processing):
				self.ratos_echo(echo_prefix, "reading gcode file...")

			slicer = self.get_slicer_info(lines)
			slicer_name = slicer["Name"]
			slicer_version = slicer["Version"]

			if (not enable_post_processing and slicer_name == UNKNOWN_SLICER):
				return True

			if (enable_post_processing):
				if slicer_name != PRUSA_SLICER and slicer_name != SUPER_SLICER and slicer_name != ORCA_SLICER:
					raise self.printer.command_error("Unsupported Slicer")

			min_x = 1000
			max_x = 0
			first_x = -1
			first_y = -1
			toolshift_count = 0
			tower_line = -1
			start_print_line = 0
			file_has_changed = False
			wipe_accel = 0
			used_tools = []
			pause_counter = 0
			extruder_temps = []
			extruder_temps_line = 0
			for line in range(len(lines)):
				# give the cpu some time
				pause_counter += 1
				if pause_counter == 1000:
					pause_counter = 0
					self.reactor.pause(.001)

				# get slicer profile settings
				if (enable_post_processing):
					if slicer_name == PRUSA_SLICER:
						if wipe_accel == 0:
							if lines[line].rstrip().startswith("; wipe_tower_acceleration = "):
								wipe_accel = int(lines[line].rstrip().replace("; wipe_tower_acceleration = ", ""))

				# get the start_print line number
				if start_print_line == 0:
					if lines[line].rstrip().startswith("START_PRINT") or lines[line].rstrip().startswith("RMMU_START_PRINT"):
						lines[line] = lines[line].replace("#", "") # fix color variable format
						start_print_line = line

				# fix superslicer and orcaslicer other layer temperature bug
				if (enable_post_processing):
					if start_print_line > 0 and extruder_temps_line == 0:
						if slicer_name == SUPER_SLICER or slicer_name == ORCA_SLICER:
							if lines[line].rstrip().startswith("_ON_LAYER_CHANGE LAYER=2"):
								extruder_temps_line = line
								pattern = r"EXTRUDER_OTHER_LAYER_TEMP=([\d,]+)"
								matches = re.search(pattern, lines[start_print_line].rstrip())
								if matches:
									extruder_temps = matches.group(1).split(",")

				# fix orcaslicer set acceleration gcode command
				if (enable_post_processing):
					if start_print_line > 0 and slicer_name == ORCA_SLICER:
						if lines[line].rstrip().startswith("SET_VELOCITY_LIMIT"):
							pattern = r"ACCEL=(\d+)"
							matches = re.search(pattern, lines[line].rstrip())
							if matches:
								accel = matches.group(1)
								lines[line] = 'M204 S' + str(accel) + ' ; Changed by RatOS post processor: ' + lines[line].rstrip() + '\n'

				# count toolshifts
				if (enable_post_processing):
					if start_print_line > 0:
						if lines[line].rstrip().startswith("T") and lines[line].rstrip()[1:].isdigit():
							if toolshift_count == 0:
								lines[line] = REMOVED_BY_POST_PROCESSOR + lines[line].rstrip() + '\n' # remove first toolchange
							toolshift_count += 1

				# get first tools usage in order
				if (enable_post_processing):
					if start_print_line > 0:
						if len(used_tools) == 0:
							index = lines[start_print_line].rstrip().find("INITIAL_TOOL=")
							if index != -1:
								used_tools.append(lines[start_print_line].rstrip()[index + len("INITIAL_TOOL="):].split()[0])
						if lines[line].rstrip().startswith("T") and lines[line].rstrip()[1:].isdigit():
							# add tool to the list if not already added
							t = lines[line].rstrip()[1:]
							if t not in used_tools:
								used_tools.append(t)

				# get first XY coordinates
				if start_print_line > 0 and first_x < 0 and first_y < 0:
					if lines[line].rstrip().startswith("G1") or lines[line].rstrip().startswith("G0"):
						split = lines[line].rstrip().replace("  ", " ").split(" ")
						for s in range(len(split)):
							if split[s].lower().startswith("x"):
								try:
									x = float(split[s].lower().replace("x", ""))
									if x > first_x:
										first_x = x
								except Exception as exc:
									self.ratos_echo(echo_prefix, "Can not get first x coordinate. " + str(exc))
									return False
							if split[s].lower().startswith("y"):
								try:
									y = float(split[s].lower().replace("y", ""))
									if y > first_y:
										first_y = y
								except Exception as exc:
									self.ratos_echo(echo_prefix, "Can not get first y coordinate. " + str(exc))
									return False
					if (not enable_post_processing):
						if (first_x >= 0 and first_y >= 0):
							self.gcode.run_script_from_command("SET_GCODE_VARIABLE MACRO=START_PRINT VARIABLE=first_x VALUE=" + str(first_x))
							self.gcode.run_script_from_command("SET_GCODE_VARIABLE MACRO=START_PRINT VARIABLE=first_y VALUE=" + str(first_y))
							return True

				# get x boundaries 
				if (enable_post_processing):
					if start_print_line > 0:
						if lines[line].rstrip().startswith("G1") or lines[line].rstrip().startswith("G0"):
							split = lines[line].rstrip().replace("  ", " ").split(" ")
							for s in range(len(split)):
								if split[s].lower().startswith("x"):
									try:
										x = float(split[s].lower().replace("x", ""))
										if x < min_x:
											min_x = x
										if x > max_x:
											max_x = x
									except Exception as exc:
										self.ratos_echo(echo_prefix, "Can not get x boundaries . " + str(exc))
										return False

				# toolshift processing
				if (enable_post_processing):
					if start_print_line > 0:
						if lines[line].rstrip().startswith("T") and lines[line].rstrip()[1:].isdigit():

							# purge tower
							if tower_line == -1:
								tower_line = 0
								for i2 in range(20):
									if lines[line-i2].rstrip().startswith("; CP TOOLCHANGE START"):
										tower_line = line-i2
										break

							# z-hop before toolchange
							zhop = 0
							zhop_line = 0
							if tower_line == 0:
								for i2 in range(20):
									if slicer_name == PRUSA_SLICER or slicer_name == SUPER_SLICER:
										if lines[line-i2].rstrip().startswith("; custom gcode: end_filament_gcode"):
											if lines[line-i2-1].rstrip().startswith("G1 Z"):
												split = lines[line-i2-1].rstrip().split(" ")
												if split[1].startswith("Z"):
													zhop = float(split[1].replace("Z", ""))
													if zhop > 0.0:
														zhop_line = line-i2-1
														break
									elif slicer_name == ORCA_SLICER:
										if lines[line+i2].rstrip().startswith("G1 Z"):
											split = lines[line+i2].rstrip().split(" ")
											if split[1].startswith("Z"):
												zhop = float(split[1].replace("Z", ""))
												if zhop > 0.0:
													zhop_line = line+i2
													break

							# toolchange line
							toolchange_line = 0
							for i2 in range(20):
								if lines[line + i2].rstrip().startswith("T") and lines[line].rstrip()[1:].isdigit():
									toolchange_line = line + i2
									break

							# toolchange retraction
							retraction_line = 0
							retraction_z_hop_line = 0
							if tower_line == 0 and toolchange_line > 0:
								for i2 in range(20):
									if slicer_name == PRUSA_SLICER or slicer_name == SUPER_SLICER:
										if lines[toolchange_line + i2].rstrip().startswith("G1 E-"):
											retraction_line = toolchange_line + i2
											if lines[toolchange_line + i2 + 1].rstrip().startswith("G1 Z"):
												retraction_z_hop_line = toolchange_line + i2 + 1
											break
									elif slicer_name == ORCA_SLICER:
										if lines[toolchange_line - i2].rstrip().startswith("G1 E-"):
											retraction_line = toolchange_line - i2
											break

							# move after toolchange
							move_x = ''
							move_y = ''
							move_line = 0
							move_z_hop_line = 0
							if toolchange_line > 0:
								for i2 in range(20):
									if lines[toolchange_line + i2].rstrip().replace("  ", " ").startswith("G1 X"):
										splittedstring = lines[toolchange_line + i2].rstrip().replace("  ", " ").split(" ")
										if splittedstring[1].startswith("X"):
											if splittedstring[2].startswith("Y"):
												move_x = splittedstring[1].rstrip()
												move_y = splittedstring[2].rstrip()
												move_line = toolchange_line + i2
												if slicer_name == PRUSA_SLICER or slicer_name == SUPER_SLICER:
													if lines[toolchange_line + i2 - 1].rstrip().startswith("G1 Z"):
														move_z_hop_line = toolchange_line + i2 - 1
												break

							# z-drop after toolchange
							move_z = ''
							zdrop_line = 0
							if tower_line == 0:
								if slicer_name == PRUSA_SLICER or slicer_name == SUPER_SLICER:
									if lines[move_line + 1].rstrip().startswith("G1 Z"):
										zdrop_line = move_line + 1
									elif lines[move_line + 2].rstrip().startswith("G1 Z"):
										zdrop_line = move_line + 2
									if zdrop_line > 0:
										split = lines[zdrop_line].rstrip().split(" ")
										if split[1].startswith("Z"):
											move_z = split[1].rstrip()
								elif slicer_name == ORCA_SLICER:
									if zhop_line > 0:
										for i in range(5):
											if lines[zhop_line+i].rstrip().startswith("G1 Z"):
												for i2 in range(5):
													if lines[zhop_line+i+i2].rstrip().startswith("G1 Z"):
														zdrop_line = zhop_line+i+i2
														split = lines[zdrop_line].rstrip().split(" ")
														if split[1].startswith("Z"):
															move_z = split[1].rstrip()

							# extrusion after move
							extrusion_line = 0
							if tower_line == 0 and move_line > 0:
								for i2 in range(5):
									if lines[move_line + i2].rstrip().startswith("G1 E"):
										extrusion_line = move_line + i2
										break

							# make toolshift changes
							if toolshift_count > 0 and toolchange_line > 0 and move_line > 0:
								file_has_changed = True
								if zhop_line > 0:
									lines[zhop_line] = REMOVED_BY_POST_PROCESSOR + lines[zhop_line].rstrip() + '\n'
									if slicer_name == ORCA_SLICER:
										for i in range(5):
											if lines[zhop_line+i].rstrip().startswith("G1 Z"):
												lines[zhop_line+i] = REMOVED_BY_POST_PROCESSOR + lines[zhop_line+i].rstrip() + '\n'
												break
								if zdrop_line > 0:
									lines[zdrop_line] = REMOVED_BY_POST_PROCESSOR + lines[zdrop_line].rstrip() + '\n'
								if self.rmmu_hub == None:
									new_toolchange_gcode = (lines[toolchange_line].rstrip() + ' ' + move_x + ' ' + move_y + ' ' + move_z).rstrip()
								else:
									new_toolchange_gcode = ('TOOL T=' + lines[toolchange_line].rstrip().replace("T", "") + ' ' + move_x.replace("X", "X=") + ' ' + move_y.replace("Y", "Y=") + ' ' + move_z.replace("Z", "Z=")).rstrip()
								lines[toolchange_line] = new_toolchange_gcode + '\n'
								# --------------------------------------------------------------------------------
								# temporarily outcommented to fix gcode render issues in gcode viewer applications
								# the toolshift already moves the toolhead to this position but this wont be reflected in viewer applications
								# originally outcommented to avoid microstuttering for ultra fast toolshifts
								# needs to be tested if microstuttering is still an issue
								# --------------------------------------------------------------------------------
								# lines[move_line] = REMOVED_BY_POST_PROCESSOR + lines[move_line].rstrip().replace("  ", " ") + '\n'
								# --------------------------------------------------------------------------------
								if move_z_hop_line > 0:
									lines[move_z_hop_line] = REMOVED_BY_POST_PROCESSOR + lines[move_z_hop_line].rstrip() + '\n'
								if retraction_line > 0 and extrusion_line > 0:
									lines[retraction_line] = REMOVED_BY_POST_PROCESSOR + lines[retraction_line].rstrip() + '\n'
									lines[extrusion_line] = REMOVED_BY_POST_PROCESSOR + lines[extrusion_line].rstrip() + '\n'
									if retraction_z_hop_line > 0:
										lines[retraction_z_hop_line] = REMOVED_BY_POST_PROCESSOR + lines[retraction_z_hop_line].rstrip() + '\n'

			# add START_PRINT parameters 
			if (enable_post_processing):
				if start_print_line > 0:
					if toolshift_count > 0:
						file_has_changed = True
						lines[start_print_line] = lines[start_print_line].rstrip() + ' TOTAL_TOOLSHIFTS=' + str(toolshift_count - 1) + '\n'
					if first_x >= 0 and first_y >= 0:
						file_has_changed = True
						lines[start_print_line] = lines[start_print_line].rstrip() + ' FIRST_X=' + str(first_x) + ' FIRST_Y=' + str(first_y) + '\n'
					if min_x < 1000:
						file_has_changed = True
						lines[start_print_line] = lines[start_print_line].rstrip() + ' MIN_X=' + str(min_x) + ' MAX_X=' + str(max_x) + '\n'
					if len(used_tools) > 0:
						file_has_changed = True
						lines[start_print_line] = lines[start_print_line].rstrip() + ' USED_TOOLS=' + ','.join(used_tools) + '\n'
						lines[start_print_line] = lines[start_print_line].rstrip() + ' WIPE_ACCEL=' + str(wipe_accel) + '\n'
						# fix super slicer inactive toolhead other layer temperature bug
						if len(extruder_temps) > 0:
							for tool in used_tools:
								lines[extruder_temps_line] = lines[extruder_temps_line] + "M104 S" + str(extruder_temps[int(tool)]) + " T" + str(tool) + "\n"
							for i in range(10):
								if lines[extruder_temps_line + i].rstrip().startswith("M104 S"):
									lines[extruder_temps_line + i] = REMOVED_BY_POST_PROCESSOR + lines[extruder_temps_line + i].rstrip() + '\n'
									break

					# console output 
					self.ratos_echo(echo_prefix, "USED TOOLS: " + ','.join(used_tools))
					self.ratos_echo(echo_prefix, "TOOLSHIFTS: " + str(0 if toolshift_count == 0 else toolshift_count - 1))
					self.ratos_echo(echo_prefix, "SLICER: " + slicer_name + " " + slicer_version)

					# save file if it has changed 
					if file_has_changed:
						lines.append("; processed by RatOS\n")
						self.save_gcode_file(path, lines)

			if (enable_post_processing):
				self.ratos_echo(echo_prefix, "Done!")
		except:
			self.ratos_echo(echo_prefix, "Post processing error!")
		return True

	def gcode_already_processed(self, path):
		readfile = None
		try:
			with open(path, "r") as readfile:
				for line in readfile:
					pass
				return line.rstrip().lower().startswith("; processed by ratos")
		except:
			raise self.printer.command_error("Can not get processed state")
		finally:
			readfile.close()

	def get_slicer_info(self, lines):
		try:
			index = 0
			if not lines[0].rstrip().lower().startswith("; generated by"):
				if lines[1].rstrip().lower().startswith("; generated by"):
					index = 1
				else:
					return {"Name": UNKNOWN_SLICER, "Version": ""}
			line = lines[index].rstrip().replace("; generated by ", "")
			split = line.split(" on ")[0]
			return {"Name": split.split(" ")[0].lower(), "Version": split.split(" ")[1]}
		except:
			raise self.printer.command_error("Can not get slicer version")

	def get_gcode_file_info(self, filename):
		files = self.v_sd.get_file_list(True)
		flist = [f[0] for f in files]
		files_by_lower = { filepath.lower(): [filepath, fsize] for filepath, fsize in files }
		filepath = filename
		try:
			if filepath not in flist:
				filepath = files_by_lower[filepath.lower()]
				return filepath
			fullpath = os.path.join(self.sdcard_dirname, filepath);
			return [fullpath, os.path.getsize(fullpath)]
		except:
			raise self.printer.command_error("Can not get path for file " + filename)

	def get_gcode_file_lines(self, filepath):
		try:
			with open(filepath, "r", encoding='UTF-8') as readfile:
				return readfile.readlines()
		except:
			raise self.printer.command_error("Unable to open file")
		finally:
			readfile.close()

	def save_gcode_file(self, path, lines):
		writefile = None
		try:
			pause_counter = 0
			with open(path, "w", newline='\n', encoding='UTF-8') as writefile:
				for i, strline in enumerate(lines):
					pause_counter += 1
					if pause_counter == 1000:
						pause_counter = 0
						self.reactor.pause(.001)
					writefile.write(strline)
		except Exception as exc:
			raise self.printer.command_error("FileWriteError: " + str(exc))
		finally:
			writefile.close()

	#####
	# Helper
	#####
	def ratos_echo(self, prefix, msg):
		self.gcode.run_script_from_command("RATOS_ECHO PREFIX=" + str(prefix) + " MSG='" + str(msg) + "'")

	def debug_echo(self, prefix, msg):
		self.gcode.run_script_from_command("DEBUG_ECHO PREFIX=" + str(prefix) + " MSG='" + str(msg) + "'")

	def get_is_graph_files(self):
		try:
			folder_path = r"/home/pi/printer_data/config/input_shaper/"
			file_type = r"*.png"
			return glob.glob(os.path.join(folder_path, file_type))
		except Exception as exc:
			self.debug_echo("get_is_graph_files", "Something went wrong. " + str(exc))
		return None
	
	def get_ratos_version(self):
		version = '?'
		path = pathlib.Path('/home/pi/printer_data/config/RatOS/.git')
		gitdir = os.path.join(path, '..')
		prog_desc = ('git', '-C', gitdir, 'describe', '--always',
					'--tags', '--long', '--dirty')
		prog_status = ('git', '-C', gitdir, 'status', '--porcelain', '--ignored')
		try:
			process = subprocess.Popen(prog_desc, stdout=subprocess.PIPE,
									stderr=subprocess.PIPE)
			ver, err = process.communicate()
			retcode = process.wait()
			if retcode == 0:
				version = str(ver.strip().decode())
				process = subprocess.Popen(prog_status, stdout=subprocess.PIPE,
										stderr=subprocess.PIPE)
				retcode = process.wait()
				return version
			else:
				self.debug_echo("get_ratos_version", ("Error getting git version: %s", err))
		except Exception as exc:
			self.debug_echo("get_ratos_version", ("Exception on run: %s", exc))
		return version

#####
# Bed Mesh Profile Manager
#####
class BedMeshProfileManager:
	def __init__(self, config, bedmesh):
		self.name = "bed_mesh"
		self.printer = config.get_printer()
		self.gcode = self.printer.lookup_object('gcode')
		self.bedmesh = bedmesh
		self.profiles = {}
		self.incompatible_profiles = []
		# Fetch stored profiles from Config
		stored_profs = config.get_prefix_sections(self.name)
		stored_profs = [s for s in stored_profs
						if s.get_name() != self.name]
		for profile in stored_profs:
			name = profile.get_name().split(' ', 1)[1]
			version = profile.getint('version', 0)
			if version != BedMesh.PROFILE_VERSION:
				logging.info(
					"bed_mesh: Profile [%s] not compatible with this version\n"
					"of bed_mesh.  Profile Version: %d Current Version: %d "
					% (name, version, BedMesh.PROFILE_VERSION))
				self.incompatible_profiles.append(name)
				continue
			self.profiles[name] = {}
			zvals = profile.getlists('points', seps=(',', '\n'), parser=float)
			self.profiles[name]['points'] = zvals
			self.profiles[name]['mesh_params'] = params = \
				collections.OrderedDict()
			for key, t in BedMesh.PROFILE_OPTIONS.items():
				if t is int:
					params[key] = profile.getint(key)
				elif t is float:
					params[key] = profile.getfloat(key)
				elif t is str:
					params[key] = profile.get(key)
	def get_profiles(self):
		return self.profiles
	def load_profile(self, prof_name):
		profile = self.profiles.get(prof_name, None)
		if profile is None:
			return None
		probed_matrix = profile['points']
		mesh_params = profile['mesh_params']
		z_mesh = BedMesh.ZMesh(mesh_params, prof_name)
		try:
			z_mesh.build_mesh(probed_matrix)
		except BedMesh.BedMeshError as e:
			raise self.gcode.error(str(e))
		return z_mesh

#####
# Loader
#####
def load_config(config):
	return RatOS(config)
