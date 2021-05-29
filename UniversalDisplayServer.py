import sys



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
        return true
    else:
        return false 

def on_message(client, userdata, msg):
    #global players
#    print "Topic: ",msg.topic+'\nMessage: '+str(msg.payload)
    if msg.topic == 'squeezebox/control':
        if msg.payload == 'PLAY':
            for player in range(len(players)):
                players[player].play()
        elif msg.payload == 'STOP':
           for player in range(len(players)):
                players[player].stop()
        # Temporarily use players[0] as the player being controlled.  <<-- TO FIX
        # Need to include the player name in the mqtt message.
        elif msg.payload == 'NEXT':
            print players[0]
            players[0].next()
        elif msg.payload == 'PREV':
            players[0].prev()
        elif msg.payload == 'PAUSE':
            players[0].pause()
            print('paused ...')
        elif msg.payload == 'VOLUP':
            players[0].volume_up(1)
        elif msg.payload == 'VOLDN':
            players[0].volume_down(1)

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
            print 'Logged in: %s' % squeezeServer.logged_in
            print 'Version: %s' % squeezeServer.get_version()
        except Exception as e:
            print('Oops!', e.__class__, 'occured')
            # wait before retrying
            print('LMS not online. Retrying ...')
            time.sleep(1)

#    print(time.time())

#    if squeezeServer.get_player(player_name):
#	print("player is available")
    # Note: there seems to be a lengthy delay between a playey becoming unavailable 
    #       and get_player() no longer registering it - bug in pylms???
#    while squeezeServer.get_player(player_name):  # Only contine if there is a player, otherwise errors occur.
    # Check if number of players has changed.
#    print(time.time())
#    print('Real Player count: %s' %squeezeServer.get_player_count())


    try:
        if squeezeServer.get_player_count() != len(players):
#            players = {}
            player_count = squeezeServer.get_player_count()
            #print('Player count: %s' %player_count)
            for player in squeezeServer.get_players():
                ref = player.get_ref()
                if ref not in players:
                    players[ref] = player
                    print("Adding mode for player %s" %ref)
                    mode[ref] = player.get_mode()
                    current_track[ref] = None # Initialise this variable for use later.
            print('System reported player count: %s' %player_count)
            print('Tracked player count: %s' %len(players))
            if player_count <> len(players):
                print ('WARNING ... WARNING ... WARNING: Player count currpution')
            print('Modes %s' %mode)
            print(players)
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




    available_players = squeezeServer.get_players()  # returns a list of player ojects
    ap_refs = []
    for ap in available_players:
        ap_refs.append(ap.get_ref())  # build a list of the references of availabel players
#    print(available_players, type(available_players), available_players[0].get_ref(), type(available_players[0].get_ref()))
#    print(players[available_players[0].get_ref()], type(players[available_players[0].get_ref()]))
#    if available_players[0].get_ref() in players.keys():
#        print("yeah")
    # add new players
    for ap in available_players:
        if ap.get_ref() not in  players.keys():
            players[ap.get_ref()] = ap
    # remove disconnected players from the list of tracked players
    for tp in players.keys():
        if tp not in ap_refs:
            del players[tp]





    if player_count > 0:
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
            if track[ref] != current_track[ref]:
                try:
                    #publish.single('/squeezebox/display_pool', '%s - %s :%d:' %(artist,track, time_elapsed), hostname='192.168.1.151')
                    client.publish('squeezebox/' + players[ref].get_name() + '/track', '%s - %s' %(artist[ref],track[ref]))
                    print ("New song %s - %s" %(artist[ref],track[ref]))
                    current_track[ref] = track[ref]
                except Exception, e:
                    print 'Exception type is %s.' %(e)
                    # Reconnect to display.
                    #display_connected = connectToDisplay()

            # Send a message if the mode has changed.
            currentMode[ref] = players[ref].get_mode()
            if currentMode[ref] != mode[ref]:
                client.publish('squeezebox/' + players[ref].get_name() + '/mode', currentMode[ref])
                mode[ref] = currentMode[ref]
                print mode[ref]
                print('Modes %s' %mode[ref])

    time.sleep(1.01)  # reduce CPU useage by slowing down the loop.

    LastRefresh = datetime.datetime.now()
