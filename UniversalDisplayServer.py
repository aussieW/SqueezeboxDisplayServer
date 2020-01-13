from pylms import server
import time
import datetime
import paho.mqtt.client as MQTT
#import paho.mqtt.publish as publish

# Define Globals
MQTTServer = '192.168.1.49'
LMSServer = '192.168.1.1'

def on_connect(client, userdata, flags, rc):
    print("connected with result code "+str(rc))
    if rc==0:
        client.subscribe('squeezebox/control')
        return true
    else:
       return false 

def on_message(client, userdata, msg):
    print "Topic: ",msg.topic+'\nMessage: '+str(msg.payload)
    if msg.topic == 'squeezebox/control':
        if msg.payload == 'PLAY':
            player.play()
        elif msg.payload == 'STOP':
            player.stop()
        elif msg.payload == 'NEXT':
            player.next()
        elif msg.payload == 'PREV':
            player.prev()
        elif msg.payload == 'PAUSE':
            player.pause()
        elif msg.payload == 'VOLUP':
            player.volume_up(1)
        elif msg.payload == 'VOLDN':
            player.volume_down(1)

# Connect to the Logitech Media Server
squeezeServer = server.Server(LMSServer)
squeezeServer.connect()
print 'Logged in: %s' % squeezeServer.logged_in
print 'Version: %s' % squeezeServer.get_version()

# Connect to the MQTT Server
client = MQTT.Client("DisplayServer")
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(username='hassio', password='myhassio')
client.connect(MQTTServer,1883,60)

player_count = 0
display_enabled = False
#player_name = 'RPiPool'
#player_name = 'study'
#player_name = 'Pool'
#player_name = 'hoytsFormalRoom'
players = []
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
#    print('Outside loop')
    # Process MQTT network events.
#    client.loop()

#    if squeezeServer.get_player(player_name):
#	print("player is available")
    # Note: there seems to be a lengthy delay between a playey becoming unavailable 
    #       and get_player() no longer registering it - bug in pylms???
#    while squeezeServer.get_player(player_name):  # Only contine if there is a player, otherwise errors occur.
    # Check if number of players has changed.
#    print(time.time())
#    print('Real Player count: %s' %squeezeServer.get_player_count())
    if squeezeServer.get_player_count() != len(players):
        players = []
        player_count = squeezeServer.get_player_count()
        for player in squeezeServer.get_players():
            players.append(player)
            mode[player] = player.get_mode()
            current_track[player] = player.get_track_current_title()
            print('Player count: %s' %player_count)
            print('Modes %s' %mode)
            print(players)
#    print(time.time())

    if player_count > 0:
#        print(time.time())
#        client.loop()
#        print(time.time())

        for player in players:
#            client.loop()
            # Send the current track info.
            try:
                artist[player] = player.get_track_artist()
            except UnicodeEncodeError:
                # pylms throws an error when unknown ASCII characters are encountered.
                artist[player] = '???'
                print('Artist unicode error')
            try:
                track[player] = player.get_track_current_title()
            except UnicodeEncodeError:
                # pylms throws an error when unknown ASCII characters are encountered.
                track[player] = '???'
                print('Track unicode error')
            if time.time() > elapsed_time_delay + 1.0:  # Limit checking to once per second
                try:
                    time_elapsed = int(player.get_time_elapsed())
                    time_remaining = int(player.get_time_remaining())
                    client.publish('squeezebox/' + player.get_name() + '/remaining', '%s' %time_remaining)
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
            if track[player] != current_track[player]:
                try:
                    #publish.single('/squeezebox/display_pool', '%s - %s :%d:' %(artist,track, time_elapsed), hostname='192.168.1.151')
                    client.publish('squeezebox/' + player.get_name() + '/track', '%s - %s' %(artist[player],track[player]))
                    print ("New song %s - %s" %(artist[player],track[player]))
                    current_track[player] = track[player]
                except Exception, e:
                    print 'Exception type is %s.' %(e)
                    # Reconnect to display.
                    #display_connected = connectToDisplay()

#            print(time.time())
            # Send a message if the mode has changed.
            currentMode[player] = player.get_mode()
            if currentMode[player] != mode[player]:
                client.publish('squeezebox/' + player.get_name() + '/mode', currentMode[player])
                mode[player] = currentMode[player]
                print mode[player]
                print('Modes %s' %mode[player])
#            print(time.time())
