# Jackie's Map
# CMDR Jackie Silver, DISC
# Kay Johnston 2017 / 3303
# Thanks are due to everyone who's collected data for the various source lists, and particularly to edsm.

version = '3q'

# Standard Python imports.  Might need to change PIL to pillow on some versions of Python?
from tkinter import *
import PIL
from PIL import ImageTk, Image, ImageDraw, ImageFont
import math

# From Alot's excellent edts suite.
import pgnames

# Wants, needs, options:
############

# Sort out mousewheel zoom bindings on Linux.  Should be <Button-4> and <Button-5> but ought to rework the whole event handler doodah.

# Maybe something to show the sphere of (presumed) Thargoid hyperspace interdictions.  Do we even know its extent?
# Does the hyperdiction sphere intersect with the UA sphere?
# UPs supposed to be at "Ammonia planets in the Pleiades sector" and a number of convoys near Sol.  I've added known examples, but can't verify yet.

# Add in proc-gen nebulae - at least the major ones like Colonia.  Serious effort needed to run all them down though.  Can I get this from edsm?
# Can we increase speed by drawing only those objects which are inside the canvas area?
# Add some kind of scale?  And maybe a compass pointer towards the Core?  Can lump this into Misc.
# Add rough indicator for hyperdiction sphere extent.
# Check Imperial Bubble extent and centrepoint.  Perhaps add something to show Agri (terraformed ELW) and High Tech radii.
# Add category indicators for tourist POI.
# An "approximate density" function; would need to plug in the spiral approximation for the galaxy's shape and do a bunch of other stuff.
# Continue to update the various data files.

# Other
# I should probably use setattr, and I could certainly lump all the different classes together into one uberclass.
# Could farm the cross-drawing bits out to separate method like the hats.

# Changelog
############

# 3i changes:
# Added scaling buttons, sector name check with Alot's edts, display of galmap style coordinates.
# Added display of body and latitude + longitude for POI.

# 3j changes:
# Added permit-locked HA stars to POI list and appropriate display.  Added distance display.  Added rare goods.  Minor tweaks.
# Added some known UP locations.  Corrected error with NGC 752 / IC 1848.

# 3k changes: (released version)
# Added pulsars.  Updated tourist file.  Changed mouseover to take account of scaling and only return objects which are drawn.
# Moved display of rare goods distance and tonnage into mouseover.  Removed redundant indicator text and associated button.

# 3l changes:
# Added player factions.  Updated tourist file, POI file.

# 3m changes:
# General tidying up, some UI changes.  Updated data.  Added toggle for Reorte-Riedquat line.  Finished first pass of checking player factions.
# Changed player factions sheet to include a validity option, so details for some are loaded but not used.
# Reworked to show central nebulae and stars of ha sectors; the list of central stars is incomplete, and needs work.

# 3n changes:
# Moved RR line and UA sphere into a single Misc category.  Added rough indicator of the Bubble's size into the same category.
# Added PRE logistics and Colonia stations to POIs.  Added possible boundary lines for Guardian sites towards Regor.  Added EAFOTS box to misc.
# Added distance indicators for tourist destinations.  Improved drawing of sector fills.

# 3o changes: (released version)
# Adding non-sector HA star clusters gleaned from edsm (as the galmap search is a little strange);
# Changed handling of sectors from original list which don't exist as sectors.  Introduced category for sectors which are nominally clusters but aren't.
# Added option to display the full list of individual stars known to edsm.  Very interesting to see.

# 3p changes:
# Added search and highlight/filter functions.  Added suppression corridor boundaries to misc toggle.  Enabled PG sector name finding in search.
# Enabled filtering by sector including PG sectors.  Added output .csv of filtered stars.  Draws PG sector boundaries if searched.
# ...and disabled suppression corridor boundaries again.

# 3q / 3q2 changes:
# Improved name matching on HA sector filtering.  Cleaned up line drawing stuff a bit.  Added many Grauniad sites to POI list.  Updated tourist sites.
# Updated edsm star list.  Added new Colonia systems to POI list.

class App():

    def __init__(self,master):

        # Create a frame for the controls.
        self.control_frame = Frame(master)
        self.control_frame.pack()

        # Defaults for offsets and scaling.
        self.x_offset = 0
        self.y_offset = 0
        self.z_offset = 0
        self.scaling = 2
        
        # Search defaults.
        self.search_x = 0
        self.search_y = 0
        self.search_performed = False
        self.search_target = ''
        self.highlight_target = ''
        self.search_is_pg_sector = False
        self.search_is_pg_x = 0
        self.search_is_pg_y = 0
        self.search_is_pg_z = 0 # Won't be needed, I suppose.

        # Filtering default.
        self.deferred = [] # Holds all stars that match the filter *and* match filtering by sector.
        self.deferred_alpha = [] # Holds all stars that match the filter.  (This is the first pass done, hence alpha.  Go with it.)

        # Create entry boxes for the controls.
        self.x_co_box = Entry_Box(self.control_frame,'X:',str(self.x_offset),2,9)
        self.y_co_box = Entry_Box(self.control_frame,'Y:',str(self.y_offset),2,9)
        self.z_co_box = Entry_Box(self.control_frame,'Z:',str(self.z_offset),2,9)
        self.scaling_box = Entry_Box(self.control_frame,'Scaling:',str(self.scaling),7,5)

        # Bind the control entry boxes to the automatic update.
        self.x_co_box.entry.bind('<Return>', self.auto_calculate)
        self.y_co_box.entry.bind('<Return>', self.auto_calculate)
        self.z_co_box.entry.bind('<Return>', self.auto_calculate)
        self.scaling_box.entry.bind('<Return>', self.auto_calculate)

        # Create a "save png" button.
        self.save_button = Button(self.control_frame, text = 'Output', command = self.save, padx = 1)
        self.save_button.pack(side = LEFT)

        # Create buttons for moving z levels.
        self.z_up_button = Button(self.control_frame, text = 'Z+', command = self.z_up, padx = 1)
        self.z_up_button.pack(side = LEFT)
        self.z_down_button = Button(self.control_frame, text = 'Z-', command = self.z_down, padx = 1)
        self.z_down_button.pack(side = LEFT)

        # Create buttons for changing scaling.
        self.s_up_button = Button(self.control_frame, text = 'Zm Out', command = self.s_up, padx = 1)
        self.s_up_button.pack(side = LEFT)
        self.s_down_button = Button(self.control_frame, text = 'Zm In', command = self.s_down, padx = 1)
        self.s_down_button.pack(side = LEFT)

        # Create a frame to hold toggle buttons.
        self.toggle_frame = Frame(master)
        self.toggle_frame.pack()
        
        # Create toggle buttons.
        self.draw_crosses = IntVar()
        self.draw_crosses.set(0)
        self.toggle_crosses = Checkbutton(self.toggle_frame, text = 'Crosses', variable = self.draw_crosses, command = self.update_image)
        self.toggle_crosses.pack(side = LEFT)

        self.draw_fills = IntVar()
        self.toggle_fills = Checkbutton(self.toggle_frame, text = 'Fills', variable = self.draw_fills, command = self.update_image)
        self.toggle_fills.pack(side = LEFT)

        self.draw_names = IntVar()
        self.draw_names.set(1)
        self.toggle_names = Checkbutton(self.toggle_frame, text = 'Names', variable = self.draw_names, command = self.update_image)
        self.toggle_names.pack(side = LEFT)

        self.draw_indicators = IntVar()
        self.draw_indicators.set(1)
        self.toggle_indicators = Checkbutton(self.toggle_frame, text = 'Indics', variable = self.draw_indicators, command = self.update_image)
        self.toggle_indicators.pack(side = LEFT)

        self.draw_poi = IntVar()
        self.draw_poi.set(0)
        self.toggle_poi = Checkbutton(self.toggle_frame, text = 'POI', variable = self.draw_poi, command = self.update_image)
        self.toggle_poi.pack(side = LEFT)

        self.draw_tourist = IntVar()
        self.draw_tourist.set(0)
        self.toggle_tourist = Checkbutton(self.toggle_frame, text = 'Tourist', variable = self.draw_tourist, command = self.update_image)
        self.toggle_tourist.pack(side = LEFT)

        self.draw_rares = IntVar()
        self.draw_rares.set(0)
        self.toggle_rares = Checkbutton(self.toggle_frame, text = 'Rares', variable = self.draw_rares, command = self.update_image)
        self.toggle_rares.pack(side = LEFT)

        self.draw_pulsars = IntVar()
        self.draw_pulsars.set(0)
        self.toggle_pulsars = Checkbutton(self.toggle_frame, text = 'PSR', variable = self.draw_pulsars, command = self.update_image)
        self.toggle_pulsars.pack(side = LEFT)

        self.draw_player = IntVar()
        self.draw_player.set(0)
        self.toggle_players = Checkbutton(self.toggle_frame, text = 'Plyr', variable = self.draw_player, command = self.update_image)
        self.toggle_players.pack(side = LEFT)

        self.draw_misc = IntVar()
        self.draw_misc.set(0)
        self.toggle_misc = Checkbutton(self.toggle_frame, text = 'Misc', variable = self.draw_misc, command = self.update_image)
        self.toggle_misc.pack(side = LEFT)

        self.draw_findiv = IntVar()
        self.draw_findiv.set(0)
        self.toggle_findiv = Checkbutton(self.toggle_frame, text = 'F!', variable = self.draw_findiv, command = self.update_image)
        self.toggle_findiv.pack(side = LEFT)

        # Create a frame to hold search and highlight controls.
        self.search_frame = Frame(master)
        self.search_frame.pack()

        # Create highlight - well, filter - and search boxes.
        self.highlight_box = Entry_Box(self.search_frame,'Filter','',6,10)
        self.filter_by_box = Entry_Box(self.search_frame,'by Sector','',8,10)
        self.search_box = Entry_Box(self.search_frame,'Search','',6,10)

        # Create a label to show the search result.
        self.search_result = StringVar()
        self.search_result.set('')
        self.search_result_label = Label(self.search_frame, textvariable = self.search_result,width = 32)
        self.search_result_label.pack()

        # Bind highlight and search to update functions.
        self.highlight_box.entry.bind('<Return>', self.auto_calculate)
        self.filter_by_box.entry.bind('<Return>', self.auto_calculate)
        self.search_box.entry.bind('<Return>', self.update_search_target)

        # Create a frame to display data.
        self.data_frame = Frame(master)
        self.data_frame.pack()

        # Create a label for mouse coordinates.
        self.data_mouse = StringVar()
        mousetext = 'X: --- ly, Y: --- ly, Z: --- ly.'
        self.data_mouse.set(mousetext)
        self.data_mouse_label = Label(self.data_frame, textvariable = self.data_mouse)
        self.data_mouse_label.pack()

        # Create a frame to display current sectors.
        self.current_sector_frame = Frame(master)
        self.current_sector_frame.pack()

        # Create a label to display current sectors.
        self.current_sectors = StringVar()
        self.current_sectors.set('')
        self.current_sectors_label = Label(self.current_sector_frame, textvariable = self.current_sectors, width = 82)
        self.current_sectors_label.pack()

        # Create a frame to display current tourist destinations.  (Holds current POI as well to save UI space.)
        self.current_tourist_frame = Frame(master)
        self.current_tourist_frame.pack()

        # Create a label to display current tourist destinations.
        self.current_tourists = StringVar()
        self.current_tourists.set('')
        self.current_tourists_label = Label(self.current_tourist_frame, textvariable = self.current_tourists, width = 82)
        self.current_tourists_label.pack()

        # Create a frame to show the map.
        self.map_frame = Frame(master)
        self.map_frame.pack()

        # Load in a font.
        self.fnt = ImageFont.truetype('Quicksand-Regular.otf', FONTSIZE)

        # Create a canvas to show the map image.
        self.map_canvas = Canvas(self.map_frame, width = XDIM, height = YDIM)
        self.map_canvas.pack()

        self.map_canvas_mx = 0
        self.map_canvas_my = 0

        # Bind mouse actions to the canvas.
        self.map_canvas.bind('<Motion>',self.motion)
        self.map_canvas.bind('<Button-1>',self.click)
        self.map_canvas.bind_all('<MouseWheel>',self.mousewheel_zoom)

        # Once everything else is done, call a function to update the display.
        self.update_image()

    def motion(self,event):
        self.map_canvas_mx, self.map_canvas_my = event.x, event.y

        # Arcane maneouvres to convert mouse position to map position.
        mx_min = self.x_offset - (XDIM / 2 * self.scaling)
        my_max = self.y_offset + (YDIM / 2 * self.scaling)

        mx_calc = mx_min + (self.map_canvas_mx * self.scaling)
        my_calc = my_max - (self.map_canvas_my * self.scaling)

        mx_calc = round(mx_calc,1)
        my_calc = round(my_calc,1)

        # Display the calculated position.
        mousetext = 'X: ' + str(mx_calc) + ' ly, Y: ' + str(my_calc)
        mousetext += ' ly, Z: ' + str(self.z_offset) + ' ly.'

        mousetext += '    (Galmap:  ' + str(mx_calc) + ', ' + str(self.z_offset) + ', ' + str(my_calc) + ' )'

        # Calculate distance from Sol for the display.
        d_from_sol = ((mx_calc ** 2) + (my_calc ** 2) + (self.z_offset ** 2)) ** 0.5
        if d_from_sol < 1000:
            d_text = str(int(d_from_sol)) + ' ly from Sol.'
        else:
            d_text = str(round(d_from_sol / 1000,1)) + ' Kylies from Sol.'
            
        mousetext += '    ' + d_text
              
        self.data_mouse.set(mousetext)

        # Clear search box.
        self.search_result.set('')

        # Reworked section; find the single primary ha sector at the current position.
        current = single_member_of(mx_calc, my_calc, self.z_offset)

        # Use edts to get the sector name at the current position.
        vector_alot = pgnames.vector3.Vector3(mx_calc, self.z_offset, my_calc)
        # If the coordinates are too far out this can start to return odd values or fail, hence try-except.
        try:
            sector_alot = pgnames.get_sector_name(vector_alot) # as (x,z,y)
            sector_alot = str(sector_alot).upper()
        except:
            sector_alot = ''

        # We have a list of known ha sectors.  If edts would give an ha sector, ignore it.
        # Ideally I'd like one proc-gen name and all HA names, sorted in order.
        if sector_alot not in known_ha_secs:
            builttext = sector_alot
        else:
            builttext = ''

        builttext += current

        # Clunky.
        for sector in ha_sec_list:
            if sector.name == builttext:
                if sector.a_nebula != '':
                    builttext += '  -  Nebula:  ' + sector.a_nebula
                if sector.a_star != '':
                    builttext += '  -  Search:  ' + sector.a_star
        
        self.current_sectors.set(builttext)

        # Work out which tourist POI are at the current position. (2d only)
        d_lr = self.draw_poi.get()
        d_pr = self.draw_pulsars.get()
        d_ra = self.draw_rares.get()
        d_to = self.draw_tourist.get()
        d_pf = self.draw_player.get()
        d_fi = self.draw_findiv.get()
        ht = self.highlight_target
        current = current_tourist(mx_calc, my_calc, self.scaling, d_lr, d_pr, d_ra, d_to, d_pf, d_fi,ht,self.deferred)
        # For goodness sake move this inside the class!

        builttext = ''
        for destination in current:
            if destination != '':
                builttext += destination
                builttext += ', '
        builttext = builttext.rstrip(', ')
        
        self.current_tourists.set(builttext[:110])

    def mousewheel_zoom(self,event):

        # Check that this works under Linux (&Mac OS if possible)

        # At the moment, this is zooming in or out by one level each time.
        # Could change it to take account of the full delta given.
        if event.delta > 0:
            self.scaling = self.scaling / ZOOMSPEED
        else:
            self.scaling = self.scaling * ZOOMSPEED

        # Update the scaling box to show the new value.
        self.scaling_box.entry.delete(0,END)
        self.scaling_box.entry.insert(0,self.scaling)
        
        self.update_image()

    # Move down z levels when the button is pressed.
    def z_down(self):
        self.z_offset -= Z_MOVE_RATE
        self.z_co_box.entry.delete(0,END)
        self.z_co_box.entry.insert(0,self.z_offset)
        
        self.update_image()

    # Move up z levels when the button is pressed.
    def z_up(self):
        self.z_offset += Z_MOVE_RATE
        self.z_co_box.entry.delete(0,END)
        self.z_co_box.entry.insert(0,self.z_offset)
        
        self.update_image()

    # Increase scaling factor (zoom out) when the button is pressed.
    def s_up(self):
        self.scaling *= S_MOVE_RATE
        # Update the scaling box to show the new value.
        self.scaling_box.entry.delete(0,END)
        self.scaling_box.entry.insert(0,self.scaling)

        self.update_image()

    # Decrease scaling factor (zoom in) when the button is pressed.
    def s_down(self):
        self.scaling /= S_MOVE_RATE
        # Update the scaling box to show the new value.
        self.scaling_box.entry.delete(0,END)
        self.scaling_box.entry.insert(0,self.scaling)

        self.update_image()

    def click(self,event):
        self.map_canvas_mx, self.map_canvas_my = event.x, event.y

        # Arcane maneouvres to convert mouse position to map position.
        mx_min = self.x_offset - (XDIM / 2 * self.scaling)
        my_max = self.y_offset + (YDIM / 2 * self.scaling)

        mx_calc = mx_min + (self.map_canvas_mx * self.scaling)
        my_calc = my_max - (self.map_canvas_my * self.scaling)

        # In this case, we are moving to the new position.
        # So I'm rounding to 1 dp in the interests of common sense.
        mx_calc = round(mx_calc,1)
        my_calc = round(my_calc,1)
        
        self.x_offset = mx_calc
        self.y_offset = my_calc
        
        self.x_co_box.entry.delete(0,END)
        self.x_co_box.entry.insert(0,mx_calc)
        
        self.y_co_box.entry.delete(0,END)
        self.y_co_box.entry.insert(0,my_calc)
        
        mousetext = 'X: ' + str(mx_calc) + ' ly, Y: ' + str(my_calc)
        mousetext += ' ly, Z: ' + str(self.z_offset) + ' ly.'

        self.data_mouse.set(mousetext)

        self.update_image()

    def update_search_target(self,A):

        self.search_is_pg_sector = False
        self.search_is_pg_x = 0
        self.search_is_pg_y = 0
        self.search_is_pg_z = 0
        self.search_target = str(self.search_box.entry.get())
        stu = self.search_target.upper()

        found_rough = False
        found_exact = False
        rx = 0
        ry = 0
        rz = 0
        rn = ''
        ex = 0
        ey = 0
        ez = 0
        en = ''
        cx = 0
        cy = 0
        cz = 0

        # A list of lists - we will search through each of these in turn looking for a match.
        search_lists = [[findiv_list,'Sys'],[pulsar_list,'Psr'],[tourist_list,'Trst'],[player_list,'Plyr'],[rares_list,'RG'],[poi_list,'POI'],[ha_sec_list,'Sct']]

        for sl in search_lists:
        
            # Search through this list.
            for f in sl[0]:
                if stu == f.name.upper():
                    ex = f.x
                    ey = f.y
                    ez = f.z
                    en = 'Found: ' + f.name + ' (' + sl[1] + ')'
                    found_exact = True
                elif stu in f.name.upper():
                    rx = f.x
                    ry = f.y
                    rz = f.z
                    rn = 'Try: ' + f.name + ' (' + sl[1] + ')'
                    found_rough = True

            # If we have an exact match, update the entry boxes.
            if found_exact == True:
                self.x_co_box.entry.delete(0,END)
                self.x_co_box.entry.insert(0,ex)
                
                self.y_co_box.entry.delete(0,END)
                self.y_co_box.entry.insert(0,ey)

                self.z_co_box.entry.delete(0,END)
                self.z_co_box.entry.insert(0,ez)

                cx = ex
                cy = ey
                cz = ez

                self.search_result.set(en)
                self.search_x = cx
                self.search_y = cy
                self.search_performed = True
                
            elif found_rough == True:
                self.x_co_box.entry.delete(0,END)
                self.x_co_box.entry.insert(0,rx)
                
                self.y_co_box.entry.delete(0,END)
                self.y_co_box.entry.insert(0,ry)

                self.z_co_box.entry.delete(0,END)
                self.z_co_box.entry.insert(0,rz)

                self.search_result.set(rn)
                self.search_x = rx
                self.search_y = ry
                self.search_performed = True

                cx = rx
                cy = ry
                cz = rz

            else:
                # Might want to move this to an earlier point, so that rough matches in other names don't take precedence.
                try:
                    pg_sector = pgnames.get_sector(stu,False)
                    
                    # Offsets as the pg sectors ain't centred on Sol.
                    wx = (pg_sector.x * 1280) - 65
                    wy = (pg_sector.z * 1280) - 1065
                    wz = (pg_sector.y * 1280) - 25
                    wx += 640
                    wy += 640
                    wz += 640

                    self.x_co_box.entry.delete(0,END)
                    self.x_co_box.entry.insert(0,wx)
                    
                    self.y_co_box.entry.delete(0,END)
                    self.y_co_box.entry.insert(0,wy)

                    self.z_co_box.entry.delete(0,END)
                    self.z_co_box.entry.insert(0,wz)

                    self.search_result.set('Found: ' + pg_sector.name + ' (PG)')
                    self.search_x = wx
                    self.search_y = wy
                    self.search_performed = True

                    self.search_is_pg_sector = True
                    self.search_is_pg_x = wx - 640
                    self.search_is_pg_y = wy + 640
                    self.search_is_pg_z = wz - 640

                    cx = wx
                    cy = wy
                    cz = wz
                    
                except:
                    self.search_result.set('No match found.')
                    
                    

        cx = round(cx,1)
        cy = round(cy,1)
        cz = round(cz,1)

        # Clunky bit, as we need to update the position shown to reflect the new coordinates.
        # Display the calculated position.
        mousetext = 'X: ' + str(cx) + ' ly, Y: ' + str(cy)
        mousetext += ' ly, Z: ' + str(cz) + ' ly.'

        mousetext += '    (Galmap:  ' + str(cx) + ', ' + str(cz) + ', ' + str(cy) + ' )'

        # Calculate distance from Sol for the display.
        d_from_sol = ((cx ** 2) + (cy ** 2) + (cz ** 2)) ** 0.5
        if d_from_sol < 1000:
            d_text = str(int(d_from_sol)) + ' ly from Sol.'
        else:
            d_text = str(round(d_from_sol / 1000,1)) + ' Kylies from Sol.'
            
        mousetext += '    ' + d_text
              
        self.data_mouse.set(mousetext)

        self.auto_calculate(A)

    def auto_calculate(self,A):

        self.x_offset = float(self.x_co_box.entry.get())
        self.y_offset = float(self.y_co_box.entry.get())
        self.z_offset = float(self.z_co_box.entry.get())
        self.scaling = float(self.scaling_box.entry.get())

        self.search_target = str(self.search_box.entry.get()) # Redundant now?
        self.highlight_target = str(self.highlight_box.entry.get())
        self.filter_by_target = str(self.filter_by_box.entry.get())

        # Check to see which stars fall within the highlight and filtering parameters.
        dp = self.draw_pulsars.get() # Moved here for speed.
        self.deferred_alpha = []
        self.deferred = []

        # First we refine the list to only those stars whose name fits the filter.
        for f in findiv_list:
            if self.highlight_target != '':
                if self.highlight_target.upper() in f.name.upper():
                    self.deferred_alpha.append(f)
                elif self.highlight_target == '*':
                    self.deferred_alpha.append(f)

        # Look to see if we have a proc-gen sector.
        found_pg = False
        wname = ''
        try:
            pg_sector = pgnames.get_sector(self.filter_by_target,False)
            # Offsets as the pg sectors ain't centred on Sol.
            wname = pg_sector.name
            # Gets the south-west-down corner.
            wx_swd = (pg_sector.x * 1280) - 65
            wy_swd = (pg_sector.z * 1280) - 1065
            wz_swd = (pg_sector.y * 1280) - 25
            found_pg = True
            # Get the north-east-up corner.  Or possible NEU!
            wx_neu = wx_swd + 1280
            wy_neu = wy_swd + 1280
            wz_neu = wz_swd + 1280
        except:
            found_pg = False

        if found_pg == False:
            # Now refine by sector.  This only checks through HA sectors.
            for d in self.deferred_alpha:
                if self.filter_by_target != '':
                    d_is_in = single_member_of(d.x,d.y,d.z)
                    if self.filter_by_target.upper() in d_is_in.upper():
                        self.deferred.append(d)
                else:
                    self.deferred.append(d)
        else:
            # This checks if we are in the boundaries of the given PG sector.
            # Need to make sure that the stars are not in an HA sector instead.
            for d in self.deferred_alpha:
                if d.x >= wx_swd and d.x <= wx_neu:
                    if d.y >= wy_swd and d.y <= wy_neu:
                        if d.z >= wz_swd and d.z <= wz_neu:
                            # Use edts to get the sector name at the current position.
                            vector_alot = pgnames.vector3.Vector3(d.x, d.z, d.y)
                            # If the coordinates are too far out this can start to return odd values or fail, hence try-except.
                            try:
                                sector_alot = pgnames.get_sector_name(vector_alot) # as (x,z,y)
                            except:
                                sector_alot = ''
                            if sector_alot.upper() == wname.upper():
                                self.deferred.append(d)

        if self.highlight_target != '':
            self.draw_findiv.set(1)

        self.update_image()

    def update_image(self):
        # Create a new image in PIL.
        self.pil_image = Image.new('RGBA',(XDIM,YDIM),'white')
        self.draw = ImageDraw.Draw(self.pil_image)

        # Use galmap image as background? - could do, but confusing tbh.  Make a toggle?

        # Want to add axis lines for x or y = 0
        x_axis = self.x_offset / self.scaling
        y_axis = self.y_offset / self.scaling

        self.draw.line(((XDIM/2 - x_axis,0),(XDIM/2 - x_axis,YDIM)), fill = 'gray', width = 1)
        self.draw.line(((0,YDIM/2 + y_axis),(XDIM,YDIM/2 + y_axis)), fill = 'gray', width = 1)

        # Want to draw the UA sphere.
        if self.draw_misc.get() == 1:
            cp_x = -78.6 - self.x_offset
            cp_y = -340.5 - self.y_offset

            adj_x = XDIM/2 + (cp_x / self.scaling)
            adj_y = YDIM/2 - (cp_y / self.scaling)

            # Need to get "r on this z level"; draw inner boundary at 130 ly (?) - needs rechecking
            r_z = radius_on_plane(-149.6,130,self.z_offset)

            if r_z > 0:
                adj_r = r_z / self.scaling

                self.draw.ellipse(((adj_x-adj_r,adj_y-adj_r),(adj_x+adj_r,adj_y+adj_r)), outline = (255,0,255,255))

            # Need to get "r on this z level"; draw outer boundary at 150 ly (?) - needs rechecking
            r_z = radius_on_plane(-149,150,self.z_offset)

            if r_z > 0:
                adj_r = r_z / self.scaling

                self.draw.ellipse(((adj_x-adj_r,adj_y-adj_r),(adj_x+adj_r,adj_y+adj_r)), outline = (255,0,255,255))

        # Want to draw the Bubble extent.
        if self.draw_misc.get() == 1:
            cp_x = 0 - self.x_offset
            cp_y = 0 - self.y_offset

            adj_x = XDIM/2 + (cp_x / self.scaling)
            adj_y = YDIM/2 - (cp_y / self.scaling)

            r_z = radius_on_plane(0,200,self.z_offset)

            if r_z > 0:
                adj_r = r_z / self.scaling

                self.draw.ellipse(((adj_x-adj_r,adj_y-adj_r),(adj_x+adj_r,adj_y+adj_r)), outline = (0,0,255,255))

            # And let's add one around Achenar, see if that works...
            cp_x = 67.5 - self.x_offset
            cp_y = 24.8 - self.y_offset

            adj_x = XDIM/2 + (cp_x / self.scaling)
            adj_y = YDIM/2 - (cp_y / self.scaling)

            r_z = radius_on_plane(-119.5,100,self.z_offset)

            if r_z > 0:
                adj_r = r_z / self.scaling

                self.draw.ellipse(((adj_x-adj_r,adj_y-adj_r),(adj_x+adj_r,adj_y+adj_r)), outline = (0,0,255,255))

            # And a little one for Colonia.  If I need many more of these, should do them with a list.
            cp_x = -9530.5 - self.x_offset
            cp_y = 19808.1 - self.y_offset

            adj_x = XDIM/2 + (cp_x / self.scaling)
            adj_y = YDIM/2 - (cp_y / self.scaling)

            r_z = radius_on_plane(-910.3,40,self.z_offset)

            if r_z > 0:
                adj_r = r_z / self.scaling

                self.draw.ellipse(((adj_x-adj_r,adj_y-adj_r),(adj_x+adj_r,adj_y+adj_r)), outline = (0,0,255,255))

        # Draw the Reorte-Riedquat line.
        if self.draw_misc.get() == 1:
            # Riedquat (68.84375, 69.75, 48.75)
            # Reorte (75.75, 75.15625, 48.75)

            # Get the midpoint between Reorte and Riedquat.
            midpoint_x = 72.296875
            midpoint_y = 72.453125

            # Get the slope of the line between Reorte and Riedquat.
            x_diff = 75.75 - 68.84375
            y_diff = 75.15625 - 69.75

            line_start_x = midpoint_x - (RR_LENGTH * x_diff)
            line_start_y = midpoint_y - (RR_LENGTH * y_diff)

            line_end_x = midpoint_x + (RR_LENGTH * x_diff)
            line_end_y = midpoint_y + (RR_LENGTH * y_diff)

            line_start_x -= self.x_offset
            line_start_y -= self.y_offset

            line_end_x -= self.x_offset
            line_end_y -= self.y_offset

            ri_x = line_start_x
            ri_y = line_start_y

            re_x = line_end_x
            re_y = line_end_y

            adj_ls_x = XDIM/2 + (line_start_x / self.scaling)
            adj_ls_y = YDIM/2 - (line_start_y / self.scaling)

            adj_le_x = XDIM/2 + (line_end_x / self.scaling)
            adj_le_y = YDIM/2 - (line_end_y / self.scaling)

            self.draw.line(((adj_ls_x,adj_ls_y),(adj_le_x,adj_le_y)), fill = (0,0,255,255))

        # Draw (possible!) Guardians lines to Regor.
        if self.draw_misc.get() == 1:
            # Regor north about (1100,-30,-150), Regor south about (1100,-150,-150)
            self.doline(290,-7.9,1100,-30,(255,0,255,255))
            self.doline(290,-62.2,1100,-236,(255,0,255,255))

        # Draw current progress of Bright Star survey project.
        if self.draw_misc.get() == 1:
            self.doline(0,0,-8000,10000,(255,0,0,255))

        # Draw Suppression corridor boundaries.  (~x,y +/- 1100 ly Sol relative)  Possibly add "Neutron field" rough extent markers?
        # Disabled for the moment - need a better grasp on the shape.
##        if self.draw_misc.get() == 1:
##            x_axis_l = -380 - self.x_offset # This narrow boundary is roughly the distance from Sadge you need to go to see stellar remnants.
##            x_axis_r = 410 - self.x_offset
####            y_axis_l = -1100 + self.y_offset
####            y_axis_r = 1100 + self.y_offset
##
##            adj_x_l = XDIM/2 + (x_axis_l / self.scaling)
##            adj_x_r = XDIM/2 + (x_axis_r / self.scaling)
####            adj_y_l = YDIM/2 + (y_axis_l / self.scaling)
####            adj_y_r = YDIM/2 + (y_axis_r / self.scaling)
##
##            self.draw.line(((adj_x_l,0),(adj_x_l,YDIM)), fill = 'gray', width = 1)
##            self.draw.line(((adj_x_r,0),(adj_x_r,YDIM)), fill = 'gray', width = 1)
##
####            self.draw.line(((0,adj_y_l),(XDIM,adj_y_l)), fill = 'gray', width = 1)
####            self.draw.line(((0,adj_y_r),(XDIM,adj_y_r)), fill = 'gray', width = 1)

        # Draw EAFOTS box.
        if self.draw_misc.get() == 1:
            # Southwest (-6466,-6186), northeast (-5186,-4906)
            ne_x = -5186 - self.x_offset
            ne_y = -4906 - self.y_offset
            
            sl = 1280

            sw_x = ne_x - sl
            sw_y = ne_y - sl

            adj_ne_x = XDIM/2 + (ne_x / self.scaling)
            adj_ne_y = YDIM/2 - (ne_y / self.scaling)

            adj_sw_x = XDIM/2 + (sw_x / self.scaling)
            adj_sw_y = YDIM/2 - (sw_y / self.scaling)

            box = ((adj_ne_x,adj_ne_y), (adj_sw_x,adj_sw_y))
            self.draw.rectangle(box, outline = (255,0,255,255))                                      
                    
        # Iterates through drawing known pulsars.
        if self.draw_pulsars.get() == 1:
            for psr in pulsar_list:
                
                cp_x = psr.x - self.x_offset
                cp_y = psr.y - self.y_offset

                adj_x = XDIM/2 + (cp_x / self.scaling)
                adj_y = YDIM/2 - (cp_y / self.scaling)

                nametext = psr.name

                if psr.status == 'Invisible':
                    psr_colour = (200,100,100,255)
                elif psr.status == 'Permit-locked':
                    psr_colour = (255,0,0,255)
                else:
                    psr_colour = (10,140,190,255)

                star_colour = (160,160,160,255)
                
                if abs(self.z_offset - psr.z) < PSR_Z_RANGE:
                    self.draw.ellipse(((adj_x-PSRSIZE,adj_y-PSRSIZE),(adj_x+PSRSIZE,adj_y+PSRSIZE)), fill = psr_colour)
                    self.draw.line(((adj_x - 2,adj_y - 2),(adj_x + 2,adj_y + 2)), fill = star_colour, width = 1)
                    self.draw.line(((adj_x - 2,adj_y + 2),(adj_x + 2,adj_y - 2)), fill = star_colour, width = 1)
                    self.draw.line(((adj_x,adj_y - 3),(adj_x,adj_y + 3)), fill = star_colour, width = 1)
                    self.draw.line(((adj_x - 3,adj_y),(adj_x + 3,adj_y)), fill = star_colour, width = 1)

                    if self.draw_names.get() == 1: # Could control this with a separate button.
                        self.draw.text((adj_x + FONTSIZE/2,adj_y - FONTSIZE/2),nametext,font = self.fnt,fill = psr_colour)

                else:
                    self.draw.ellipse(((adj_x-PSRSIZE,adj_y-PSRSIZE),(adj_x+PSRSIZE,adj_y+PSRSIZE)), fill = psr_colour)
                    self.draw.line(((adj_x - 2,adj_y - 2),(adj_x + 2,adj_y + 2)), fill = star_colour, width = 1)
                    self.draw.line(((adj_x - 2,adj_y + 2),(adj_x + 2,adj_y - 2)), fill = star_colour, width = 1)
                    self.draw.line(((adj_x,adj_y - 3),(adj_x,adj_y + 3)), fill = star_colour, width = 1)
                    self.draw.line(((adj_x - 3,adj_y),(adj_x + 3,adj_y)), fill = star_colour, width = 1)

                    self.draw_hat(psr.z,adj_x,adj_y,psr_colour)

        # Reworked bit for drawing filtered stars.
        dp = self.draw_pulsars.get()
        if self.draw_findiv.get() == 1:
            if self.highlight_target != '':
                for d in self.deferred:
                    cp_x = d.x - self.x_offset
                    cp_y = d.y - self.y_offset

                    adj_x = XDIM/2 + (cp_x / self.scaling)
                    adj_y = YDIM/2 - (cp_y / self.scaling)

                    fc = (0,200,0,255)

                    if 'PSR' in d.name:
                        if dp == 0:
                            self.draw.line(((adj_x,adj_y - CROSSSIZE),(adj_x,adj_y + CROSSSIZE)),fill = fc)
                            self.draw.line(((adj_x - CROSSSIZE,adj_y),(adj_x + CROSSSIZE,adj_y)),fill = fc)
                    else:
                        self.draw.line(((adj_x,adj_y - CROSSSIZE),(adj_x,adj_y + CROSSSIZE)),fill = fc)
                        self.draw.line(((adj_x - CROSSSIZE,adj_y),(adj_x + CROSSSIZE,adj_y)),fill = fc)
            # If no filter is set, draw all stars from the full individual list.
            else:
                for f in findiv_list:
                    cp_x = f.x - self.x_offset
                    cp_y = f.y - self.y_offset

                    adj_x = XDIM/2 + (cp_x / self.scaling)
                    adj_y = YDIM/2 - (cp_y / self.scaling)
                    
                    fc = (180,180,0,255)

                    if 'PSR' in f.name:
                        if dp == 0:
                            self.draw.line(((adj_x,adj_y - CROSSSIZE),(adj_x,adj_y + CROSSSIZE)),fill = fc)
                            self.draw.line(((adj_x - CROSSSIZE,adj_y),(adj_x + CROSSSIZE,adj_y)),fill = fc)
                    else:
                        self.draw.line(((adj_x,adj_y - CROSSSIZE),(adj_x,adj_y + CROSSSIZE)),fill = fc)
                        self.draw.line(((adj_x - CROSSSIZE,adj_y),(adj_x + CROSSSIZE,adj_y)),fill = fc)
        

        # Iterates through drawing known POI.
        if self.draw_poi.get() == 1:
            for landmark in poi_list:
                cp_x = landmark.x - self.x_offset
                cp_y = landmark.y - self.y_offset

                adj_x = XDIM/2 + (cp_x / self.scaling)
                adj_y = YDIM/2 - (cp_y / self.scaling)

                nametext = landmark.name

                if landmark.poi_type == 'Powerplay':
                    lm_colour = (150,20,230,255)
                elif landmark.poi_type == 'Landmark':
                    lm_colour = (50,50,220,255)
                elif landmark.poi_type == 'Alien' or landmark.poi_type == 'Fungal':
                    lm_colour = (190,20,180,255)
                elif landmark.poi_type == 'Permit':
                    lm_colour = (255,0,0,255)
                else:
                    lm_colour = (45,180,225,255)

                if abs(self.z_offset - landmark.z) < POI_Z_RANGE:
                    self.draw.ellipse(((adj_x-POISIZE,adj_y-POISIZE),(adj_x+POISIZE,adj_y+POISIZE)), fill = lm_colour)

                    if self.draw_names.get() == 1: # Could control this with a separate button.
                        self.draw.text((adj_x + FONTSIZE/2,adj_y - FONTSIZE/2),nametext,font = self.fnt,fill = lm_colour)

                else:
                    self.draw.ellipse(((adj_x-POISIZE,adj_y-POISIZE),(adj_x+POISIZE,adj_y+POISIZE)), fill = lm_colour)

                    self.draw_hat(landmark.z,adj_x,adj_y,lm_colour)

        # Iterates through drawing known player factions.
        if self.draw_player.get() == 1:
            for pf in player_list:
                if pf.valid == 'Yes':
                    cp_x = pf.x - self.x_offset
                    cp_y = pf.y - self.y_offset

                    adj_x = XDIM/2 + (cp_x / self.scaling)
                    adj_y = YDIM/2 - (cp_y / self.scaling)

                    nametext = str(pf.name)

                    t_colour = (130,160,40,255)

                    if abs(self.z_offset - pf.z) < PF_Z_RANGE:
                        self.draw.line(((adj_x,adj_y - CROSSSIZE),(adj_x,adj_y + CROSSSIZE)),fill = t_colour)
                        self.draw.line(((adj_x - CROSSSIZE,adj_y),(adj_x + CROSSSIZE,adj_y)),fill = t_colour)

                        if self.draw_names.get() == 1:
                            self.draw.text((adj_x + FONTSIZE/4,adj_y - FONTSIZE/2),nametext,font = self.fnt,fill = t_colour)

                    else:
                        self.draw.line(((adj_x,adj_y - CROSSSIZE),(adj_x,adj_y + CROSSSIZE)),fill = t_colour)
                        self.draw.line(((adj_x - CROSSSIZE,adj_y),(adj_x + CROSSSIZE,adj_y)),fill = t_colour)

                        self.draw_hat(pf.z,adj_x,adj_y,t_colour) 
                    
        # Iterates through drawing known tourist locations.
        if self.draw_tourist.get() == 1:
            for destination in tourist_list:
                cp_x = destination.x - self.x_offset
                cp_y = destination.y - self.y_offset

                adj_x = XDIM/2 + (cp_x / self.scaling)
                adj_y = YDIM/2 - (cp_y / self.scaling)

                nametext = str(destination.number)
                if nametext == '0':
                    nametext = '?'

                t_colour = (10,110,10,255)

                if abs(self.z_offset - destination.z) < TOURIST_Z_RANGE:
                    self.draw.ellipse(((adj_x-TOURISTSIZE,adj_y-TOURISTSIZE),(adj_x+TOURISTSIZE,adj_y+TOURISTSIZE)), fill = t_colour)

                    if self.draw_names.get() == 1: # This is slow.
                        self.draw.text((adj_x + FONTSIZE/4,adj_y - FONTSIZE/2),nametext,font = self.fnt,fill = t_colour)

                else:
                    self.draw.ellipse(((adj_x-TOURISTSIZE,adj_y-TOURISTSIZE),(adj_x+TOURISTSIZE,adj_y+TOURISTSIZE)), fill = t_colour)

                    self.draw_hat(destination.z,adj_x,adj_y,t_colour) 
                    
        # Iterates through drawing known rare goods.
        if self.draw_rares.get() == 1:
            for rare in rares_list:
                cp_x = rare.x - self.x_offset
                cp_y = rare.y - self.y_offset

                adj_x = XDIM/2 + (cp_x / self.scaling)
                adj_y = YDIM/2 - (cp_y / self.scaling)

                nametext = str(rare.name)

                if rare.distance < RARE_MAX_DISTANCE:
                    t_colour = (240,90,30,255)
                else:
                    t_colour = (100,100,100,255)

                if abs(self.z_offset - rare.z) < RARE_Z_RANGE:
                    self.draw.ellipse(((adj_x-RARESIZE,adj_y-RARESIZE),(adj_x+RARESIZE,adj_y+RARESIZE)), fill = t_colour)

                    if self.draw_names.get() == 1: # This is slow.
                        self.draw.text((adj_x + FONTSIZE/4,adj_y - FONTSIZE/2),nametext,font = self.fnt,fill = t_colour)

                else:
                    self.draw.ellipse(((adj_x-RARESIZE,adj_y-RARESIZE),(adj_x+RARESIZE,adj_y+RARESIZE)), fill = t_colour)

                    self.draw_hat(rare.z,adj_x,adj_y,t_colour)

        # Iterate through drawing sector fills first.
        if self.draw_fills.get() == 1:
            for sector in ha_sec_list:
                if sector.state == 'Open':
                    fc = (0,0,0,255)
                elif sector.state == 'Permit-locked.':
                    fc = (255,0,0,255)
                else:
                    fc = (130,80,60,255) # Don't really need this but whatever.

                cp_x = sector.x - self.x_offset
                cp_y = sector.y - self.y_offset

                adj_x = XDIM/2 + (cp_x / self.scaling)
                adj_y = YDIM/2 - (cp_y / self.scaling)

                # Need to get "r on this z level"
                r_z = radius_on_plane(sector.z,sector.r,self.z_offset)

                if r_z > 0:
                    adj_r = r_z / self.scaling

                    if sector.state != 'Not found':
                        if sector.state == 'Open':
                            self.draw.ellipse(((adj_x-adj_r,adj_y-adj_r),(adj_x+adj_r,adj_y+adj_r)), fill = (255,255,255,255))
                        else:
                            self.draw.ellipse(((adj_x-adj_r,adj_y-adj_r),(adj_x+adj_r,adj_y+adj_r)), fill = fc)
        
        # Iterates through drawing known sectors.
        for sector in ha_sec_list:
            if sector.state == 'Open':
                fc = (0,0,0,255)
            elif sector.state == 'Permit-locked.':
                fc = (255,0,0,255)
            else:
                fc = (130,80,60,255) # Don't really need this but whatever.

            cp_x = sector.x - self.x_offset
            cp_y = sector.y - self.y_offset

            adj_x = XDIM/2 + (cp_x / self.scaling)
            adj_y = YDIM/2 - (cp_y / self.scaling)

            # Need to get "r on this z level"
            r_z = radius_on_plane(sector.z,sector.r,self.z_offset)

            if r_z > 0:
                adj_r = r_z / self.scaling

                if sector.state != 'Not found':
                    self.draw.ellipse(((adj_x-adj_r,adj_y-adj_r),(adj_x+adj_r,adj_y+adj_r)), outline = fc)

                    # Placeholder indicators for object types.
                    # Not drawn are LM (Landmark) and OS (Open Cluster that is sparse or non-existent on the map)
                    if self.draw_indicators.get() == 1:
                        if sector.sec_type == 'NB': # Ordinary emission nebula.
                            self.draw.ellipse(((adj_x-NEBSIZE,adj_y-NEBSIZE),(adj_x+NEBSIZE,adj_y+NEBSIZE)), fill = (230,170,50,255))
                        elif sector.sec_type == 'NX': # Ordinary emission nebula known to host barnacles.
                            self.draw.ellipse(((adj_x-NEBSIZE,adj_y-NEBSIZE),(adj_x+NEBSIZE,adj_y+NEBSIZE)), fill = (230,170,50,255), outline = (190,20,180,255))
                        elif sector.sec_type == 'PN': # Planetary nebula.
                            self.draw.ellipse(((adj_x-NEBSIZE,adj_y-NEBSIZE),(adj_x+NEBSIZE,adj_y+NEBSIZE)), fill = (70,240,240,255))
                            self.draw.line(((adj_x - 2,adj_y - 2),(adj_x + 2,adj_y + 2)), fill = (30,180,190,255), width = 1)
                            self.draw.line(((adj_x - 2,adj_y + 2),(adj_x + 2,adj_y - 2)), fill = (30,180,190,255), width = 1)
                            self.draw.line(((adj_x,adj_y - 3),(adj_x,adj_y + 3)), fill = (30,180,190,255), width = 1)
                            self.draw.line(((adj_x - 3,adj_y),(adj_x + 3,adj_y)), fill = (30,180,190,255), width = 1)
                        elif sector.sec_type == 'DN': # Dark nebula.
                            self.draw.ellipse(((adj_x-NEBSIZE,adj_y-NEBSIZE),(adj_x+NEBSIZE,adj_y+NEBSIZE)), fill = (35,30,0,255))
                        elif sector.sec_type == 'OC': # Open Cluster of stars.
                            self.draw.line(((adj_x - 2,adj_y - 2),(adj_x + 2,adj_y + 2)), fill = 'black', width = 1)
                            self.draw.line(((adj_x - 2,adj_y + 2),(adj_x + 2,adj_y - 2)), fill = 'black', width = 1)
                            self.draw.line(((adj_x,adj_y - 3),(adj_x,adj_y + 3)), fill = 'black', width = 1)
                            self.draw.line(((adj_x - 3,adj_y),(adj_x + 3,adj_y)), fill = 'black', width = 1)

            # Draw an indicator if we have a 'sector' which contains only a number of named stars.
            r_solo = radius_on_plane(sector.z,SOLO_ASSUMED_RADIUS,self.z_offset)

            if r_solo > 0:

                adj_r = r_solo / self.scaling

                if self.draw_indicators.get() == 1:
                    # Should I use a different indicator here, to avoid confusion with OC sectors?  Or not?
                    if sector.sec_type == 'ST':
                        self.draw.line(((adj_x - 2,adj_y - 2),(adj_x + 2,adj_y + 2)), fill = 'black', width = 1)
                        self.draw.line(((adj_x - 2,adj_y + 2),(adj_x + 2,adj_y - 2)), fill = 'black', width = 1)
                        self.draw.line(((adj_x,adj_y - 3),(adj_x,adj_y + 3)), fill = 'black', width = 1)
                        self.draw.line(((adj_x - 3,adj_y),(adj_x + 3,adj_y)), fill = 'black', width = 1)
                
             
        for sector in ha_sec_list:
            if sector.state == 'Open':
                fc = (0,0,0,255)
            elif sector.state == 'Permit-locked.':
                fc = (255,0,0,255)
            else:
                fc = (130,80,60,255)

            cp_x = sector.x - self.x_offset
            cp_y = sector.y - self.y_offset

            adj_x = XDIM/2 + (cp_x / self.scaling)
            adj_y = YDIM/2 - (cp_y / self.scaling)

            # Only draw text for sectors which are present on this z level.
            r_z = radius_on_plane(sector.z,sector.r,self.z_offset)

            nametext = sector.name

            if r_z > 0:
                if self.draw_names.get() == 1:
                    self.draw.text((adj_x + FONTSIZE/2,adj_y - FONTSIZE/2),nametext,font = self.fnt,fill = fc)
                    
                if self.draw_crosses.get() == 1 and sector.state == 'Not found':
                    self.draw.line(((adj_x - CROSSSIZE,adj_y - CROSSSIZE),(adj_x + CROSSSIZE,adj_y + CROSSSIZE)), fill = fc, width = CROSSWIDTH)
                    self.draw.line(((adj_x - CROSSSIZE,adj_y + CROSSSIZE),(adj_x + CROSSSIZE,adj_y - CROSSSIZE)), fill = fc, width = CROSSWIDTH)

                    self.draw_hat(sector.z,adj_x,adj_y,fc)
                                            
            else:
                if self.draw_crosses.get() == 1:
                    self.draw.line(((adj_x - CROSSSIZE,adj_y - CROSSSIZE),(adj_x + CROSSSIZE,adj_y + CROSSSIZE)), fill = fc, width = CROSSWIDTH)
                    self.draw.line(((adj_x - CROSSSIZE,adj_y + CROSSSIZE),(adj_x + CROSSSIZE,adj_y - CROSSSIZE)), fill = fc, width = CROSSWIDTH)

                    if sector.sec_type != 'ST':
                        self.draw_hat(sector.z,adj_x,adj_y,fc)

            # Draw text if we have a 'sector' which contains only a number of named stars.
            r_solo = radius_on_plane(sector.z,SOLO_ASSUMED_RADIUS,self.z_offset)

            if r_solo > 0:
                if self.draw_names.get() == 1:
                    if sector.sec_type == 'ST':
                        self.draw.text((adj_x + FONTSIZE/2,adj_y - FONTSIZE/2),nametext,font = self.fnt,fill = fc)

            else:
                if self.draw_crosses.get() == 1:
                    if sector.sec_type == 'ST':
                        self.draw.line(((adj_x - CROSSSIZE,adj_y - CROSSSIZE),(adj_x + CROSSSIZE,adj_y + CROSSSIZE)), fill = fc, width = CROSSWIDTH)
                        self.draw.line(((adj_x - CROSSSIZE,adj_y + CROSSSIZE),(adj_x + CROSSSIZE,adj_y - CROSSSIZE)), fill = fc, width = CROSSWIDTH)

                        self.draw_hat(sector.z,adj_x,adj_y,fc)

        # Draw a marker at the latest search location.
        if self.search_performed == True:
            s_x = self.search_x - self.x_offset
            s_y = self.search_y - self.y_offset

            adj_x = XDIM/2 + (s_x / self.scaling)
            adj_y = YDIM/2 - (s_y / self.scaling)

            s_col = (150,0,0,255)

            self.draw.ellipse(((adj_x-SEARCH_SIZE_I,adj_y-SEARCH_SIZE_I),(adj_x+SEARCH_SIZE_I,adj_y+SEARCH_SIZE_I)), outline = s_col)
            self.draw.ellipse(((adj_x-SEARCH_SIZE_O,adj_y-SEARCH_SIZE_O),(adj_x+SEARCH_SIZE_O,adj_y+SEARCH_SIZE_O)), outline = s_col)
            self.draw.line(((adj_x,adj_y-SEARCH_SIZE_I),(adj_x,adj_y-SEARCH_SIZE_I-S_S_EXT)),fill = s_col,width = 2)
            self.draw.line(((adj_x,adj_y+SEARCH_SIZE_I),(adj_x,adj_y+SEARCH_SIZE_I+S_S_EXT)),fill = s_col,width = 2)
            self.draw.line(((adj_x-SEARCH_SIZE_I,adj_y),(adj_x-SEARCH_SIZE_I-S_S_EXT,adj_y)),fill = s_col,width = 2)
            self.draw.line(((adj_x+SEARCH_SIZE_I,adj_y),(adj_x+SEARCH_SIZE_I+S_S_EXT,adj_y)),fill = s_col,width = 2)

            # If we have a pg sector, draw a box showing its outlines.
            if self.search_is_pg_sector == True:
                nw_x = self.search_is_pg_x - self.x_offset
                nw_y = self.search_is_pg_y - self.y_offset
                
                sl = 1280

                se_x = nw_x + sl
                se_y = nw_y - sl

                adj_nw_x = XDIM/2 + (nw_x / self.scaling)
                adj_nw_y = YDIM/2 - (nw_y / self.scaling)

                adj_se_x = XDIM/2 + (se_x / self.scaling)
                adj_se_y = YDIM/2 - (se_y / self.scaling)

                box = ((adj_nw_x,adj_nw_y), (adj_se_x,adj_se_y))
                self.draw.rectangle(box, outline = (150,0,0,255))         
            
            
        # Convert the image to one that tkinter can use, and draw it to the canvas.
        self.working_image = ImageTk.PhotoImage(self.pil_image)
        self.image_on_canvas = self.map_canvas.create_image(0, 0, anchor = NW, image = self.working_image)

    # Draws a line from one pair of coordinates to another (adjusting for offsets.)
    def doline(self,x1,y1,x2,y2,colour):
        s_x = x1 - self.x_offset
        s_y = y1 - self.y_offset
        
        e_x = x2 - self.x_offset
        e_y = y2 - self.y_offset
        
        adj_s_x = XDIM/2 + (s_x / self.scaling)
        adj_s_y = YDIM/2 - (s_y / self.scaling)

        adj_e_x = XDIM/2 + (e_x / self.scaling)
        adj_e_y = YDIM/2 - (e_y / self.scaling)

        self.draw.line(((adj_s_x,adj_s_y),(adj_e_x,adj_e_y)), fill = colour)

    def draw_hat(self,working_z,adj_x,adj_y,fc):
        if working_z > self.z_offset:
            self.draw.line(((adj_x - CROSSSIZE,adj_y - (2 * CROSSSIZE)),(adj_x,adj_y - (3 * CROSSSIZE))), fill = fc, width = CROSSWIDTH)
            self.draw.line(((adj_x,adj_y - (3 * CROSSSIZE)),(adj_x + CROSSSIZE,adj_y - (2 * CROSSSIZE))), fill = fc, width = CROSSWIDTH)
        else:
            self.draw.line(((adj_x - CROSSSIZE,adj_y + (2 * CROSSSIZE)),(adj_x,adj_y + (3 * CROSSSIZE))), fill = fc, width = CROSSWIDTH)
            self.draw.line(((adj_x,adj_y + (3 * CROSSSIZE)),(adj_x + CROSSSIZE,adj_y + (2 * CROSSSIZE))), fill = fc, width = CROSSWIDTH)

    def save(self):
        # Save a .png of the current canvas.
        filename = 'output.png'
        self.pil_image.save(filename)

        # Save a .csv file with stars in the current filter list.
        filename = 'output.csv'
        with open(filename, 'w') as opened:
            opened.write('System,X,Y,Z,GalmapX,GalmapY,GalmapZ\n')
            if self.filter_by_target != '':
                for f in self.deferred:
                    opened.write(f.name + ',')
                    opened.write(str(f.x) + ',')
                    opened.write(str(f.y) + ',')
                    opened.write(str(f.z) + ',')
                    opened.write(str(f.x) + ',')
                    opened.write(str(f.z) + ',')
                    opened.write(str(f.y))
                    opened.write('\n')
            else:
                for f in self.deferred_alpha:
                    opened.write(f.name + ',')
                    opened.write(str(f.x) + ',')
                    opened.write(str(f.y) + ',')
                    opened.write(str(f.z) + ',')
                    opened.write(str(f.x) + ',')
                    opened.write(str(f.z) + ',')
                    opened.write(str(f.y))
                    opened.write('\n')
        

# Entry boxes with an attached label.  
class Entry_Box():

    def __init__(self,master,nametext,default,w1,w2):
        # Create a frame for this entry box.
        self.frame = Frame(master, padx = 6)
        self.frame.pack(side = LEFT)

        # Create a label.
        self.label = Label(self.frame,text = nametext,width = w1)
        self.label.pack(side = LEFT)

        # Create an entry box.
        self.entry = Entry(self.frame, width = w2)
        self.entry.pack(side = LEFT)
        self.entry.insert(0,default)

# Class to hold details for the hand-authored sectors.
class ha_sec():

    def __init__(self,name,x,y,z,r,state,sec_type,priority,a_nebula,a_star):
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.r = r
        self.state = state
        self.sec_type = sec_type
        self.priority = priority
        self.a_nebula = a_nebula
        self.a_star = a_star

# Class to hold details for POI.
class poi():

    def __init__(self,name,x,y,z,poi_type,star_system,body,lat,lon):
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.poi_type = poi_type
        self.star_system = star_system
        self.body = body
        self.lat = lat
        self.lon = lon

# Class to hold details for tourist locations.
class tourist():

    def __init__(self,number,name,system,x,y,z,description,body,location,distance):
        self.number = number
        self.name = name
        self.system = system
        self.x = x
        self.y = y
        self.z = z
        self.description = description
        self.body = body # Body the POI is near or on.
        self.location = location # Whether the POI is in orbit or on the surface.
        self.distance = distance # Distance from jump-in point.

class rare():

    def __init__(self,system,station,name,quantity,x,y,z,distance):
        self.system = system
        self.station = station
        self.name = name
        self.quantity = quantity
        self.x = x
        self.y = y
        self.z = z
        self.distance = distance

class pulsar():

    def __init__(self,system,x,y,z,status):
        self.name = system
        self.x = x
        self.y = y
        self.z = z
        self.status = status

        self.distance = ((x ** 2) + (y ** 2) + (z ** 2)) ** 0.5 # Is this needed for anything?

class player_faction():

    def __init__(self,name,superpower,government,system,x,y,z,state,valid):
        self.name = name
        self.superpower = superpower
        self.government = government
        self.system = system
        self.x = x
        self.y = y
        self.z = z
        self.state = state
        self.valid = valid

class findiv():

    def __init__(self,name,x,y,z,distance):
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.distance = distance

def read_sectors_file(filename):
    ha_sec_list = []
    with open(filename,'r') as opened:
        readtext = opened.read()

    lines = readtext.split('\n')

    for line in lines:
        values = line.split(',')
        try:
            name = str(values[0])
            x = float(values[1])
            y = float(values[2])
            z = float(values[3])
            r = float(values[4])
            state = str(values[5]) # Reads whether the sector is open, locked, or one of the erroneous sectors from the original dataset.
            sec_type = str(values[6]) # Reads the type of sector - if it's an open cluster or nebula or what have you.
            priority = int(values[8])
            a_nebula = str(values[10])
            a_star = str(values[11])
            new_ha_sec = ha_sec(name,x,y,z,r,state,sec_type,priority,a_nebula,a_star)
            ha_sec_list.append(new_ha_sec)
        except:
            alice = 'do nowt'

    return ha_sec_list

def read_poi_file(filename):
    poi_list = []
    with open(filename,'r') as opened:
        readtext = opened.read()

    lines = readtext.split('\n')

    for line in lines:
        values = line.split(',')
        try:
            name = str(values[0])
            x = float(values[1])
            y = float(values[2])
            z = float(values[3])
            poi_type = str(values[4])
            star_system = str(values[5])
            body = str(values[6])
            try:
                lat = float(values[7])
                lon = float(values[8])
            except:
                lat = 0
                lon = 0

            new_poi = poi(name,x,y,z,poi_type,star_system,body,lat,lon)
            poi_list.append(new_poi)
            
        except:
            alice = 'do nowt'

    return poi_list

def read_tourist_file(filename):
    tourist_list = []
    with open(filename,'r') as opened:
        readtext = opened.read()

    lines = readtext.split('\n')

    for line in lines:
        values = line.split(',')
        try:
            number = int(values[0])
            name = str(values[1])
            system = str(values[2])
            x = float(values[3])
            y = float(values[4])
            z = float(values[5])
            description = str(values[6])

            body = str(values[8])
            location = str(values[9])
            distance = str(values[10])

            new_tourist = tourist(number,name,system,x,y,z,description,body,location,distance)
            tourist_list.append(new_tourist)

        except:
            alice = 'do nowt'

    return tourist_list

def read_rares_file(filename):
    rares_list = []
    with open(filename,'r') as opened:
        readtext = opened.read()

    lines = readtext.split('\n')

    for line in lines:
        values = line.split(',')
        try:
            system = str(values[0])
            station = str(values[1])
            name = str(values[2])
            quantity = str(values[3])
            x = float(values[4])
            y = float(values[5])
            z = float(values[6])
            distance = int(values[7])

            new_rare = rare(system,station,name,quantity,x,y,z,distance)
            rares_list.append(new_rare)
            
        except:
            alice = 'do nowt'

    return rares_list

def read_pulsars_file(filename):
    pulsar_list = []
    with open(filename, 'r') as opened:
        readtext = opened.read()

    lines = readtext.split('\n')

    for line in lines:
        values = line.split(',')
        try:
            system = str(values[0])
            x = float(values[1])
            y = float(values[2])
            z = float(values[3])
            status = str(values[4])

            new_pulsar = pulsar(system,x,y,z,status)
            pulsar_list.append(new_pulsar)

        except:
            alice = 'do nowt'

    return pulsar_list

def read_players_file(filename):
    player_list = []
    with open(filename, 'r') as opened:
        readtext = opened.read()

    lines = readtext.split('\n')

    for line in lines:
        values = line.split(',')
        try:
            name = str(values[0])
            superpower = str(values[1])
            government = str(values[2])
            system = str(values[3])
            x = float(values[4])
            y = float(values[5])
            z = float(values[6])
            state = str(values[7])

            valid = str(values[10])

            new_player_faction = player_faction(name,superpower,government,system,x,y,z,state,valid)
            player_list.append(new_player_faction)
            
        except:
            alice = 'do nowt'

    return player_list

def read_findiv_file(filename):
    findiv_list = []
    with open(filename, 'r') as opened:
        readtext = opened.read()

    lines = readtext.split('\n')

    for line in lines:
        values = line.split(',')
        try:
            name = str(values[0])
            x = float(values[1])
            y = float(values[2])
            z = float(values[3])
            distance = float(values[4])

            new_findiv = findiv(name,x,y,z,distance)
            findiv_list.append(new_findiv)

        except:
            alice = 'do nowt'

    return findiv_list
            
# Find the radius of a given sector on a given z plane.
def radius_on_plane(z,r,z_target):
    d = z - z_target
    right = (r ** 2) - (d ** 2)
    r_target = right ** 0.5
    if isinstance(r_target, (int, float)):
        r_return = round(r_target,1)
    else:
        r_return = 0
    return r_return

# Find which sectors are present at a given position.
def current_member_of(x,y,z):
    current = []
    for sector in ha_sec_list:
        sx = sector.x
        sy = sector.y
        sz = sector.z
        sr = sector.r
        if (((sx-x) ** 2) + ((sy-y) ** 2) + ((sz-z) ** 2)) < (sr ** 2):
            current.append(sector.name)
    # Reverse the list, to give the highest priority in real terms (lowest number) first.
    current.reverse()
    return current

# Find the single primary sector present at a given position.
def single_member_of(x,y,z):
    current = []
    for sector in ha_sec_list:
        sx = sector.x
        sy = sector.y
        sz = sector.z
        sr = sector.r
        if (((sx-x) ** 2) + ((sy-y) ** 2) + ((sz-z) ** 2)) < (sr ** 2):
            current.append(sector.name)
    # Reverse the list, to give the highest priority in real terms (lowest number) first.
    current.reverse()
    try:
        result = current[0]
    except:
        result = ''
    return result

# Find which tourist destinations and POI are present at a given position. (2d only)  Should maybe move this inside the main App class?
def current_tourist(x,y,scaling,d_lm,d_pr,d_ra,d_to,d_pf,d_fi,highlight_target,deferred):
    current = []
    # Might as well catch POI here as well.
    if d_lm == 1:
        for landmark in poi_list:
            lx = landmark.x
            ly = landmark.y
            lr = POIACC * scaling
            if (((lx-x) ** 2) + ((ly-y) ** 2)) < (lr ** 2):
                # This is a bit clunky.  Depending on the amount of information available on the POI, draw its system, body and lat/lon.
                if landmark.star_system != '':
                    if landmark.lon != 0 and landmark.lat != 0:
                        landmark_text = landmark.name + ' (' + landmark.star_system + ' ' + landmark.body + ' at ' + str(landmark.lat) + ',' + str(landmark.lon) + ')'
                    else:
                        landmark_text = landmark.name + ' (' + landmark.star_system + ' ' + landmark.body + ')'
                else:
                    landmark_text = landmark.name
                current.append(landmark_text)
    # And pulsars.
    if d_pr == 1:
        for psr in pulsar_list:
            px = psr.x
            py = psr.y
            pr = PSRACC * scaling
            if (((px-x) ** 2) + ((py-y) ** 2)) < (pr ** 2):
                if psr.name != '':
                    psr_text = psr.name
                    current.append(psr_text)
    # And player factions.
    if d_pf == 1:
        for pf in player_list:
            pfx = pf.x
            pfy = pf.y
            pfr = PFACC * scaling
            if (((pfx-x) ** 2) + ((pfy-y) ** 2) < (pfr ** 2)):
                if pf.name != '' and pf.valid == 'Yes':
                    pf_text = pf.name
                    pf_text += ' (' + pf.system + ')'
                    current.append(pf_text)
                
    # And might as well catch rare goods here.
    if d_ra == 1:
        for rare in rares_list:
            rx = rare.x
            ry = rare.y
            rr = RAREACC * scaling
            if (((rx-x) ** 2) + ((ry-y) ** 2)) < (rr ** 2):
                if rare.name != '':
                    rare_text = rare.name + ' (' + rare.system + ','
                    available = ' ' + rare.quantity
                    rare_text += available
                    distance = ' @ ' + str(rare.distance) + ' ls)'
                    rare_text += distance
                    current.append(rare_text)
    # Now go through the tourist destinations.  Should maybe add the bodies to this list.
    if d_to == 1:
        for destination in tourist_list:
            dx = destination.x
            dy = destination.y
            dr = TOURISTACC * scaling
            if (((dx-x) ** 2) + ((dy-y) ** 2)) < (dr ** 2):
                tourist_text = destination.name
                if destination.number != 0:
                    tourist_text += ' (#' + str(destination.number) + ', ' + destination.system
                else:
                    tourist_text += ' (#???, ' + destination.system
                if destination.body != '':
                    tourist_text += ' ' + destination.body + ' ' + destination.location
                if destination.distance != '':
                    tourist_text += ', ' + destination.distance + ' ls'
                tourist_text += ')'
                current.append(tourist_text)

    # Let's try adding from the full list of individual stars; this could be slow.
    # Need to change this to pull only from the filtered lists.
    if d_fi == 1:
        fr = FINDIVACC * scaling
        if highlight_target == '':
            for f in findiv_list:
                if (((f.x - x) ** 2) + ((f.y - y) ** 2)) < (fr ** 2):
                    findiv_text = f.name
                    current.append(findiv_text)
        else:
            for f in deferred:
                if highlight_target == '*':
                    if (((f.x - x) ** 2) + ((f.y - y) ** 2)) < (fr ** 2):
                        findiv_text = f.name
                        current.append(findiv_text)
                elif highlight_target.upper() in f.name.upper():
                    if (((f.x - x) ** 2) + ((f.y - y) ** 2)) < (fr ** 2):
                        findiv_text = f.name
                        current.append(findiv_text)
                
    return current

# Finds the nearest tourist POI that hasn't got a number yet.  Just for gathering data.
def find_nearest_unchecked(t_list,x,y,z):
    bestfit = ''
    previous = ''
    bestdistance = 1000000
    previousbest = 1000000
    for possible in t_list:
        newdistance = ((x-possible.x)**2) + ((y-possible.y)**2) + ((z-possible.z)**2)
        newdistance = newdistance ** 0.5
        if newdistance < bestdistance:
            if possible.number == 0:
                previous = bestfit
                previousbest = bestdistance
                bestdistance = newdistance
                bestfit = possible.name
    return bestfit, bestdistance, previous, previousbest

# Global variables for controlling the display.
XDIM = 580
YDIM = 580
FONTSIZE = 10
CROSSSIZE = 2 # Size of cross markers.
CROSSWIDTH = 1 # Width of line for crosses - doesn't look very good if set higher than 1, though.
NEBSIZE = 3 # Size of nebulae.
POISIZE = 2 # Size of POI markers.
POI_Z_RANGE = 52 # Z range in which a POI marker will be drawn without a hat.
PSRSIZE = 1 # Size of pulsar markers.
PSR_Z_RANGE = 52 # Z range in which a Pulsar marker will be drawn without a hat.  Could make this much larger than the others?
TOURISTSIZE = 1 # Size of Tourist markers.
TOURIST_Z_RANGE = 52 # Z range in which a Tourist marker will be drawn without a hat.
RARESIZE = 1 # Size of Rare Goods markers
RARE_Z_RANGE = 52 # Z range in which a Rare Goods marker will be drawn without a hat.
ZOOMSPEED = 2
RARE_MAX_DISTANCE = 55000 # Maximum distance that a rare good will be considered as practical.
PF_Z_RANGE = 52
RR_LENGTH = 2000 # Length of RR line to draw.
SOLO_ASSUMED_RADIUS = 110 # Effective radius of a "sector" which contains only individual named stars.
SEARCH_SIZE_I = 5 # Radius of inner search circle icon.
SEARCH_SIZE_O = 8 # Radius of outer search circle icon.
S_S_EXT = 5 # Length of search circle lines.

# Global variables for controlling the base accuracy of the mouseover searches.  Can maybe do away with these now the scaling works properly.
PSRACC = 6
POIACC = 6
RAREACC = 6
TOURISTACC = 6
PFACC = 6
FINDIVACC = 6

# Variables that control the z +/- and scaling when the buttons are pressed.
Z_MOVE_RATE = 100 # Z axis change.  Could change this to a "z-slice-size" and adjust the various XXX_Z_RANGE appropriately to half the slice size.
S_MOVE_RATE = 2 # Scaling change.

# Read sectors file.
filename = 'seclist_ra.csv'
ha_sec_list = read_sectors_file(filename)
ha_sec_list.sort(key = lambda sector:sector.priority, reverse = True)

# Compile a list of known ha sector names.
known_ha_secs = []
for sector in ha_sec_list:
    known_ha_secs.append(sector.name)

# Read poi file.
filename = 'poilist.csv'
poi_list = read_poi_file(filename)

# Read tourist file.
filename = 'tourist_3.csv'
tourist_list = read_tourist_file(filename)

# Read rare goods file.
filename = 'rares.csv'
rares_list = read_rares_file(filename)

# Read pulsars file.
filename = 'pulsars.csv'
pulsar_list = read_pulsars_file(filename)

# Read player factions file.
filename = 'pfac.csv'
player_list = read_players_file(filename)

# Read full individual stars file.
filename = 'findiv.csv'
findiv_list = read_findiv_file(filename)

# Main loop.
root = Tk()
root.title('Jackie\'s Map (v.' + version + ')')

mainapp = App(root)

root.mainloop()
