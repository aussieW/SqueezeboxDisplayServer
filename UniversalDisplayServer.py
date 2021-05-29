import sys
import json


from pylms import server
import time
import datetime
import paho.mqtt.client as MQTT
#import paho.mqtt.publish as publish

# Define Globals
MQTTServer = '192.168.1.49'
MQTTClientname = 'LMS_Display_Server'
MQTTUsername = 'hassio'
MQTTPassword = 'myhassio'
LMSServer = '192.168.1.1'
LMSRunning = False
RefreshDelay = 1  #1 second
LastRefresh = datetime.datetime.now()


def on_connect(client, userdata, flags, rc):
    print("connected with result code "+str(rc))
    if rc==0:
        client.subscribe('squeezebox/control')
        return True
    else:
        return False

def on_message(client, userdata, msg):
    #global players
    strTopic = str(msg.topic) 
    #strPayload = str(msg.payload)
    #print("Topic: "+strTopic+'\nMessage: '+strPayload)
    strPayload = "".join(chr(x) for x in msg.payload)
    print("Topic: "+strTopic+'\nMessage: '+strPayload)
    print(msg.topic, type(msg.topic))
    if msg.topic == 'squeezebox/control':
#        try:
        data = json.loads(strPayload)
            #data = "".join(chr(x) for x in data)
#        print(data)
        p = players_by_name[data["player"]]
#        print(p)
        command = data["cmnd"]
#        print(command)
#        except Exception as ex:
#            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
#            message = template.format(type(ex).__name__, ex.args)
#            return
        if command == 'PLAY':
#            print('play')
            p.play()
#            print('Made it here!!')
        elif command == 'STOP':
            p.stop()
        elif command == 'NEXT':
            p.next()
        elif command == 'PREV':
            p.prev()
        elif command == 'PAUSE':
            p.pause()
        elif command == 'VOLUP':
            p.volume_up(1)
        elif command == 'VOLDN':
            p.volume_down(1)

squeezeServer = server.Server(LMSServer)

# Connect to the MQTT Server
client = MQTT.Client(MQTTClientname)
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(username=MQTTUsername, password=MQTTPassword)
client.connect(MQTTServer,1883,60)

player_count = 0
display_enabled = False
players = {}
players_by_name = {}
player = None
current_track = {}
mode = {}
currentMode = {}
artist = {}
track = {}
elapsed_time_delay = time.time()


## Set current time back 60 seconds so that the display is update on startup
#currentTime = datetime.datetime.now() - datetime.timedelta(seconds=60)

client.loop_start()

while 1:
    if datetime.datetime.now() - datetime.timedelta(seconds=RefreshDelay) < LastRefresh:
        continue

    # Connect to the Logitech Media Server
    #print("LMSRunning = %s" %LMSRunning)
    while not LMSRunning:
        try:
            squeezeServer.connect()
            LMSRunning = True
            print('Logged in: %s' % squeezeServer.logged_in)
            print('Version: %s' % squeezeServer.get_version())
        except Exception as e:
            print('Oops!', e.__class__, 'occured')
            # wait before retrying
            print('LMS not online. Retrying ...')
            time.sleep(1)

#    print(time.time())

#    if squeezeServer.get_player(player_name):
#        print("player is available")
    # Note: there seems to be a lengthy delay between a playey becoming unavailable 
    #       and get_player() no longer registering it - bug in pylms???
#    while squeezeServer.get_player(player_name):  # Only contine if there is a player, otherwise errors occur.
    # Check if number of players has changed.
#    print(time.time())
#    print('Real Player count: %s' %squeezeServer.get_player_count())


    try:
        available_players = squeezeServer.get_players()  # returns a list of player ojects
        ap_refs = []
        for ap in available_players:
            ap_refs.append(ap.get_ref())  # build a list of the references of availabel players
        # add new players
        for ap_ref in ap_refs:
            if ap_ref not in  players.keys():
                players[ap_ref] = squeezeServer.get_player(ap_ref)
                players_by_name[squeezeServer.get_player(ap_ref).get_name()] = squeezeServer.get_player(ap_ref)
#                print('players by name: %s' %players_by_name)
#                print("Adding mode for player %s" %ap_ref)
                mode[ap_ref] = None  #players[ap_ref].get_mode()
                current_track[ap_ref] = None # Initialise this variable for use later.

        # remove disconnected players from the list of tracked players
        for tp in players.keys():
            if tp not in ap_refs:
                del players[tp]
                del mode[tp]
                del current_track[tp]
                del players_by_name[tp.get_name()]

#        print('System reported player count: %s' %player_count)
#        print('Tracked player count: %s' %len(players))
#        if player_count <> len(players):
#            print ('WARNING ... WARNING ... WARNING: Player count currpution')
#        print('Modes %s' %mode)
#        print(players)
    except ValueError:
        # There seems to be a bug in server.py::get_player_count() which passes random crap back rather than an int.
        # Just ignore it.
        print('Ignoring ValueError')
        pass
    except Exception as e:
        # Capture and handle any other error.
        print('Oops!', e.__class__, 'occured')
        # Assume squeezeServer is not running.
        print('LMS does not appear to be runnning')
        LMSRunning = False
        player_count = 0
        players = []

    if  squeezeServer.get_player_count() != len(players):
        print('WARNING ... WARNING ... WARNING: Player count currpution')



    if len(players) > 0:
#        print(time.time())
#        client.loop()
#        print(time.time())

        for ref in players:
#            print('looping...')
#            client.loop()
            # Send the current track info.
            try:
                artist[ref] = players[ref].get_track_artist()
            except UnicodeEncodeError:
                # pylms throws an error when unknown ASCII characters are encountered.
                artist[ref] = '???'
                print('Artist unicode error')
            try:
                track[ref] = players[ref].get_track_current_title()
            except UnicodeEncodeError:
                # pylms throws an error when unknown ASCII characters are encountered.
                track[ref] = '???'
                print('Track unicode error')
            if time.time() > elapsed_time_delay + 1.0:  # Limit checking to once per second
                try:
                    time_elapsed = int(players[ref].get_time_elapsed())
                    time_remaining = int(players[ref].get_time_remaining())
                    client.publish('squeezebox/' + players[ref].get_name() + '/remaining', '%s' %time_remaining)
                    elapsed_time_delay = time.time()
                except:
                    # An error will occur if the player is no longer available but is still being reported
                    #  as available by pylms - bug??
                    # Break out of the while loop and retest for player availability.
                    player_count = player_count - 1
                    print("Player is not available")
                    break
            #print '%s - %s  %s-%s' %(artist,track, time_elapsed, time_remaining)
            #print "Track",track
            #print "Current Track",current_track
            try:
                if track[ref] != current_track[ref]:
                    try:
                        #publish.single('/squeezebox/display_pool', '%s - %s :%d:' %(artist,track, time_elapsed), hostname='192.168.1.151')
                        client.publish('squeezebox/' + players[ref].get_name() + '/track', '%s - %s' %(artist[ref],track[ref]))
                        print ("New song %s - %s" %(artist[ref],track[ref]))
                        current_track[ref] = track[ref]
                    except Exception as e:
                        print('Exception type is %s.' %(e))
                        # Reconnect to display.
                        #display_connected = connectToDisplay()
            except:
                print('track %s,  current_track %s' %(track, current_track))


            # Send a message if the mode has changed.
            currentMode[ref] = players[ref].get_mode()
            if currentMode[ref] != mode[ref]:
                client.publish('squeezebox/' + players[ref].get_name() + '/mode', currentMode[ref])
                mode[ref] = currentMode[ref]
                print(mode[ref])
                print('Modes %s' %mode[ref])

    time.sleep(1.01)  # reduce CPU useage by slowing down the loop.

    LastRefresh = datetime.datetime.now()
