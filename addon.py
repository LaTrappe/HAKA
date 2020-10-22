#IconColor =#41BDF5

import os
import sys
import urllib
import urlparse
import xbmcgui
import xbmcplugin
import xbmcaddon
import requests
import json
import calendar
import time
from xbmc import log as xbmc_log
from urlparse import parse_qsl
from datetime import datetime
import iso8601

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

addon       = xbmcaddon.Addon()
addonname   = addon.getAddonInfo('name')

def build_url(query):
    return base_url + '?' + urllib.urlencode(query)

mode = args.get('mode', None)

imgIconResourcePath = os.path.join(xbmcaddon.Addon().getAddonInfo('path'),'resources','img','icon')
imgFanartResourcePath = os.path.join(xbmcaddon.Addon().getAddonInfo('path'),'resources','img','fanart')

haDomainNames = 		['automation','climate','group','light','scene','script','sensor','switch','vacuum']
haDomainSettings = 		[ False, False, False, False, False, False, False, False, False]
haDomainTranslations = 	[30005,30006,30007,30008,30009,30010,30011,30012,30013]

haServer = addon.getSetting('haServer')
haToken = addon.getSetting('haToken')

api_base = haServer + '/api'
headers = {'Authorization': 'Bearer ' + haToken, 'Content-Type': 'application/json'}

def utc_to_local(utc_dt):
	# get integer timestamp to avoid precision lost
	timestamp = calendar.timegm(utc_dt.timetuple())
	local_dt = datetime.fromtimestamp(timestamp)
	assert utc_dt.resolution >= timedelta(microseconds=1)
	return local_dt.replace(microsecond=utc_dt.microsecond)

def parse_date(event_date):
	datetime_obj = iso8601.parse_date(event_date)
	datetime_obj = utc_to_local(datetime_obj)
	dateString = datetime_obj.strftime(xbmc.getRegion('dateshort'))
	return dateString

def parse_time(event_date):
	datetime_obj = iso8601.parse_date(event_date)
	datetime_obj = utc_to_local(datetime_obj)
	timeString = datetime_obj.strftime(xbmc.getRegion('time'))
	return timeString
	
def parse_dateTime(event_date):
	return parse_date(event_date) + ' ' + parse_time(event_date)

def have_credentials():
    return haServer and haToken

def show_dialog(message):
	xbmcgui.Dialog().ok(addonname, message)

def importDomainSettings():
	if addon.getSetting('importAutomation') == 'true':
		haDomainSettings[0] = True
	if addon.getSetting('importClimate') == 'true':
		haDomainSettings[1] = True
	if addon.getSetting('importGroups') == 'true':
		haDomainSettings[2] = True
	if addon.getSetting('importLights') == 'true':
		haDomainSettings[3] = True
	if addon.getSetting('importScenes') == 'true':
		haDomainSettings[4] = True
	if addon.getSetting('importScripts') == 'true':
		haDomainSettings[5] = True
	if addon.getSetting('importSensors') == 'true':
		haDomainSettings[6] = True
	if addon.getSetting('importSwitches') == 'true':
		haDomainSettings[7] = True
	if addon.getSetting('importVacuums') == 'true':
		haDomainSettings[8] = True

def getRequest(api_ext):
	try:
		r = requests.get(api_base + api_ext, headers=headers)
		if r.status_code == 401:
			show_dialog(addon.getLocalizedString(30050)) #Error 401: Check your token
		elif r.status_code == 405:
			show_dialog(addon.getLocalizedString(30051)) #Error 405: Method not allowed
		elif r.status_code == 200:
			return r
	except:
		show_dialog(addon.getLocalizedString(30052)) #Unknown error: Check IP address or if server is online

def postRequest(api_ext, entity_id):
	try:
		api_extention = api_ext
		payload = "{\"entity_id\": \"" + entity_id + "\"}"
		r = requests.post(api_base + api_extention, headers=headers, data=payload)
		if r.status_code == 401:
			show_dialog(addon.getLocalizedString(30050)) #Error 401: Check your token
		elif r.status_code == 405:
			show_dialog(addon.getLocalizedString(30051)) #Error 405: Method not allowed
	except:
		show_dialog(addon.getLocalizedString(30052)) #Unknown error: Check IP address or if server is online
		
def browseByDomain():
	listing=[]
	isFolder = True
	
	for d in range(len(haDomainSettings)):
		if haDomainSettings[d]:
			url = build_url({'mode': 'loadfolder', 'domain': haDomainNames[d]})
			icon = os.path.join(imgIconResourcePath) + '\\' + haDomainNames[d] + '.png'
			li = xbmcgui.ListItem(addon.getLocalizedString(haDomainTranslations[d]))
			li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
			listing.append((url, li, isFolder))
	
	#GET /config
	response = getRequest('/config')
	parsedResponse = json.loads(response.text)

	result = parsedResponse['version']

	url = build_url({'mode': 'config'})
	icon = os.path.join(imgIconResourcePath, 'config.png')
	li = xbmcgui.ListItem(addon.getLocalizedString(30023) + ': ' + parsedResponse['version'])
	li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
	listing.append((url, li, isFolder))
	
	xbmcplugin.addDirectoryItems(addon_handle, listing, len(listing))
	xbmcplugin.endOfDirectory(addon_handle)
    
def loadDomain(domain):
	response = getRequest('/states')
	parsedResponse = json.loads(response.text)
	listing=[]
	isFolder = False
	searchDomainKey = domain + '.'
	vacuumService = ['start', 'stop', 'return_to_base', 'locate']
	vacuumServiceTranslations = [30040, 30041, 30042, 30043]
	
	for entity in range(len(parsedResponse)):
		if searchDomainKey in parsedResponse[entity]['entity_id']:
			entity_id = (parsedResponse[entity]['entity_id']).encode('utf-8')
			entity_state = (parsedResponse[entity]['state']).encode('utf-8')
			label = (parsedResponse[entity]['attributes']['friendly_name']).encode('utf-8')
			icon = os.path.join(imgIconResourcePath) + '\\' + domain + '.png'

			if domain == 'automation':
				if 'last_triggered' in parsedResponse[entity]['attributes']:
					if parsedResponse[entity]['attributes']['last_triggered'] is not None:
						label = label + '[CR][LIGHT]Last time triggered: ' + str(parse_dateTime(parsedResponse[entity]['attributes']['last_triggered'])) + '[/LIGHT]'
						if entity_state == 'off':
							icon = os.path.join(imgIconResourcePath,'automation_off.png')

			elif domain == 'climate':
				label = label + '[CR][LIGHT]' + entity_state + ' - '  + addon.getLocalizedString(30020) + ': ' + str(parsedResponse[entity]['attributes']['current_temperature']) + '[/LIGHT]'
				
				if entity_state == 'off':
					icon = os.path.join(imgIconResourcePath,'climate_off.png')

			elif domain == 'group':
				if entity_state == 'off':
					icon = os.path.join(imgIconResourcePath,'group_off.png')

			elif domain == 'light':
				if entity_state == 'on':
					if 'brightness' in parsedResponse[entity]['attributes']:
						brightness = int(parsedResponse[entity]['attributes']['brightness'] / 2.56)
						label = label + '[CR][LIGHT]' + addon.getLocalizedString(30021) + ': ' + str(brightness) + '%[/LIGHT]'
				else:
					icon = os.path.join(imgIconResourcePath,'light_off.png')
					
			elif domain == 'script':
				if 'last_triggered' in parsedResponse[entity]['attributes']:
					if parsedResponse[entity]['attributes']['last_triggered'] is not None:
						label = label + '[CR][LIGHT]Last time triggered: ' + str(parse_dateTime(parsedResponse[entity]['attributes']['last_triggered'])) + '[/LIGHT]'
			
			elif domain == 'sensor':
				if 'icon' in parsedResponse[entity]['attributes']:                
					if 'thermometer' in parsedResponse[entity]['attributes']['icon']:
						icon = os.path.join(imgIconResourcePath,'thermometer.png')            
					if 'mdi:battery' in parsedResponse[entity]['attributes']['icon']:
						icon = os.path.join(imgIconResourcePath,'battery.png')
					if 'water' in parsedResponse[entity]['attributes']['icon']:
						icon = os.path.join(imgIconResourcePath,'humidity.png')                    
				else:
					icon = os.path.join(imgIconResourcePath,'unknown.png')            
				label = label + ' - ' + entity_state
				if 'unit_of_measurement' in parsedResponse[entity]['attributes']:
					label = label + parsedResponse[entity]['attributes']['unit_of_measurement'] 

			elif domain == 'switch':
				if entity_state == 'off':
					icon = os.path.join(imgIconResourcePath,'switch_off.png')

			elif domain == 'vacuum': # Each for Start / Stop / Return to base / Locate
				label = '[B]' + label + '[/B][CR][LIGHT]State: ' + parsedResponse[entity]['attributes']['status'] + ' - Battery: ' + str(parsedResponse[entity]['attributes']['battery_level']) + '[/LIGHT]' 
				url = build_url({'mode': domain, 'entity_id': entity_id, 'state' : entity_state, 'service': 'toggle'})
				li = xbmcgui.ListItem(label)
				li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
				li.setProperty('IsPlayable', 'false')
				listing.append((url, li, isFolder))
					
				for s in range(len(vacuumService)):
					controlIcon = vacuumService[s] + '.png'
					icon = os.path.join(imgIconResourcePath,controlIcon)
					labelService = '[LIGHT]' + addon.getLocalizedString(vacuumServiceTranslations[s]) + '[/LIGHT]' 
					url = build_url({'mode': domain, 'entity_id': entity_id, 'state' : entity_state, 'service': vacuumService[s]})
					li = xbmcgui.ListItem(labelService)
					li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
					listing.append((url, li, isFolder))

			else:
				icon = os.path.join(imgIconResourcePath,'unknown.png')
			
			if domain != 'vacuum':
				url = build_url({'mode': domain, 'entity_id': entity_id, 'state' : entity_state })
				li = xbmcgui.ListItem(label)
				li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
				listing.append((url, li, isFolder))
	xbmcplugin.addDirectoryItems(addon_handle, listing, len(listing))
	xbmcplugin.endOfDirectory(addon_handle)

#MAIN
importDomainSettings()

if not have_credentials():
	show_dialog(addon.getLocalizedString(30053))

if mode is None:
	browseByDomain()

else:
	params = dict(parse_qsl(sys.argv[2][1:]))
	
	if mode[0] == 'loadfolder':
		loadDomain(params['domain'])
		
	elif mode[0] == 'loadgroup':
		loadGroup(params['entity_id'])
		
	elif mode[0] == 'config':
		browseByDomain()
	else:
		if mode[0] == 'automation':
			api_ext = '/services/automation/toggle'
			postRequest(api_ext, params['entity_id'])
			
		elif mode[0] == 'climate':
			if params['state'] == 'off':
				api_ext = '/services/climate/turn_on'
			else:
				api_ext = '/services/climate/turn_off'
				
			postRequest(api_ext, params['entity_id'])
			
		elif mode[0] == 'group':
			if params['state'] == 'off':
				api_ext = '/services/homeassistant/turn_on'
			else:
				api_ext = '/services/homeassistant/turn_off'
			postRequest(api_ext, params['entity_id'])

		elif mode[0] == 'light':
			api_ext = '/services/light/toggle'
			postRequest(api_ext, params['entity_id'])

		elif mode[0] == 'scene':
			api_ext = '/services/scene/turn_on'
			postRequest(api_ext, params['entity_id'])

		elif mode[0] == 'script':
			api_ext = '/services/script/turn_on'
			postRequest(api_ext, params['entity_id'])

		elif mode[0] == 'switch':
			api_ext = '/services/homeassistant/toggle'
			postRequest(api_ext, params['entity_id'])

		elif mode[0] == 'vacuum':
			api_ext = '/services/vacuum/' + params['service']
			postRequest(api_ext, params['entity_id'])

		loadDomain(mode[0])
		xbmc.executebuiltin("Container.Refresh")
