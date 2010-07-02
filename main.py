#!/usr/bin/python2.4

import logging

'''
from waveapi import model
from waveapi import robot
from waveapi import events
from waveapi import document
'''
from waveapi import appengine_robot_runner
from waveapi import element
from waveapi import events
from waveapi import ops
from waveapi import robot

import os
import cgi
import urllib
import random
import wsgiref.handlers

from google.appengine.ext import db
from google.appengine.api import xmpp
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import re
reobj = re.compile("[^/]+(?=/)")

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#######################################################################################################################################################################
#######################################################################################################################################################################
#
#     D  E  F  I  N  I  T  I  O  N  S
#
#######################################################################################################################################################################
#######################################################################################################################################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#===================================================================================
#     D a t a s t o r e
#===================================================================================

# Here we keep track which jid is subscribed to which wave.
class Subscriptions(db.Model):
  wave      = db.StringProperty()
  jid       = db.StringProperty()
  created   = db.DateTimeProperty(auto_now_add=True)

# We keep a record of the wave's title, this makes management
# via IM much easier.
class Titles(db.Model):
  wave      = db.StringProperty()
  title     = db.StringProperty()

#===================================================================================
#     _ i n v i t e
#===================================================================================

def _invite(jid):
  text = ""
  try:
    xmpp.send_invite(jid)
    return "\ninvitation has been sent to \n" + jid
  except:
    return "\nerror while sending the invitation"

#===================================================================================
#     _ e n u m e r a t e
#===================================================================================

def _enumerate(jid):
  _subscriptions = db.GqlQuery("SELECT * FROM Subscriptions WHERE jid = :1", jid)
  text = "\nsubscribed to"
  hasSubscriptions = False
  for _subscription in _subscriptions:
    hasSubscriptions = True
    wave = _subscription.wave
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get the title of this wave
    title = ""
    _waves = db.GqlQuery("SELECT * FROM Titles WHERE wave = :1", wave)
    _wave = _waves.get()
    if _wave != None:
      title = "-->" + _wave.title + "\n"
    else:
      title = "-->(unknown title)\n"
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # build description of this subscription
    text += "\n-->" + wave + "\n"+ title + "https://wave.google.com/a/wavesandbox.com/#minimized:nav,minimized:contact,minimized:search,restored:wave:" + _subscription.wave.replace('%', '%2525', 1).replace('+', '%252B', 1) + "\n"
  if hasSubscriptions:
    return text
  else:
    return "\nnot subscribed to any wave"

#===================================================================================
#     _ s u b s c r i b e
#===================================================================================

def _subscribe(jid, wave):
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # if the user is not subscribed to any wave, send an invitation
  _subscriptions = db.GqlQuery("SELECT * FROM Subscriptions WHERE jid = :1", jid)
  _subscription = _subscriptions.get()
  if _subscription == None:
    _invite(jid)
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # get the tile of this wave
  title = ""
  _waves = db.GqlQuery("SELECT * FROM Titles WHERE wave = :1", wave)
  _wave = _waves.get()
  if _wave != None:
    title = "\n-->" + _wave.title
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # check if the user is subscribed to this wave
  _subscriptions = db.GqlQuery("SELECT * FROM Subscriptions WHERE jid = :1 AND wave = :2", jid, wave)
  _subscription = _subscriptions.get()
  if _subscription == None:
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # subscribe this user to this wave
    new_subscription = Subscriptions()
    new_subscription.jid = jid
    new_subscription.wave = wave
    new_subscription.put()
    return "\nsubscribed to\n-->" + wave + title
  else:
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # notify user that he was already susbcribed to this wave
    return "\nalready subscribed to\n-->" + wave + title

#===================================================================================
#     _ u n s u b s c r i b e
#===================================================================================

def _unsubscribe(jid, wave):
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # get the tile of this wave
  title = ""
  _waves = db.GqlQuery("SELECT * FROM Titles WHERE wave = :1", wave)
  _wave = _waves.get()
  if _wave != None:
    title = "\n-->" + _wave.title
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # check if the user is subscribed to this wave
  _subscriptions = db.GqlQuery("SELECT * FROM Subscriptions WHERE jid = :1 AND wave = :2", jid, wave)
  _subscription = _subscriptions.get()
  text = ""
  if _subscription != None:
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # delete the subscription
    _subscription.delete()
    text = "\nunsubscribed from\n-->" + wave + title
  else:
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # notify the user that he was not subscribed to this wave
    text =  "\nnot subscribed to\n-->" + wave + title
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # check if there are other users subscribed to this wave
  _subscriptions2 = db.GqlQuery("SELECT * FROM Subscriptions WHERE wave = :1", wave)
  _subscription2 = _subscriptions2.get()
  if _subscription2 == None:
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # nobody is subscribed to this wave, so delete the entry
    if _wave != None:
      _wave.delete()
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  return text

#===================================================================================
#     _ u n s u b s c r i b e A l l
#===================================================================================

def _unsubscribeAll(jid):
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # get all subscriptions from this user
  _subscriptions = db.GqlQuery("SELECT * FROM Subscriptions WHERE jid = :1", jid)
  text = "\nunsubscribed from"
  hasSubscriptions = False
  for _subscription in _subscriptions:
    hasSubscriptions = True
    wave = _subscription.wave
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # get the title of this subscription
    title = ""
    _waves = db.GqlQuery("SELECT * FROM Titles WHERE wave = :1", wave)
    _wave = _waves.get()
    if _wave != None:
      title = "\n-->" + _wave.title
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # delete this subscription
    text += "\n-->" + wave + title
    _subscription.delete()
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # check if there are other users subscribed to this wave
    _subscriptions2 = db.GqlQuery("SELECT * FROM Subscriptions WHERE wave= :1", wave)
    _subscription2 = _subscriptions2.get()
    if _subscription2 == None:
      #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      # nobody is susbscibed to this wave, so delete the entry
      if _wave != None:
        _wave.delete()
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  if hasSubscriptions:
    return text
  else:
    return "\nnot subscribed to any wave"

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#######################################################################################################################################################################
#######################################################################################################################################################################
#
#     X  M  P  P
#
#######################################################################################################################################################################
#######################################################################################################################################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#===================================================================================
#     X M P P H a n d l e r
#===================================================================================

class XMPPHandler(webapp.RequestHandler):
  def post(self):
    message = xmpp.Message(self.request.POST)
    jid = reobj.match(self.request.get('from')).group()
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # remainder of the first XMPP test
    if message.body.lower() == 'hello':
      message.reply("world!")
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # enumerate all subscriptions
    elif message.body.lower() == 'enum':
      message.reply(_enumerate(jid))
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # unsubscribe
    elif message.body[0:6].lower() == 'unsub:':
      match = re.search("(?<=unsub:)[^%]+..", message.body)
      if match:
      	wave = match.group()
        message.reply(_unsubscribe(jid, wave))
      else:
        message.reply('\ncould not find a wave with that id')
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # unsubscribe from all
    elif message.body[0:6].lower() == 'unsub!':
      message.reply(_unsubscribeAll(jid))
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # enumerate commands
    elif message.body.lower() == 'help':
      message.reply('enum = enumerates subscriptions)\n\nunsub:wave_id = unsubscribes from wave_id\n\nnunsub! = unsubscribes from everything')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#######################################################################################################################################################################
#######################################################################################################################################################################
#
#     W  A  V  E
#
#######################################################################################################################################################################
#######################################################################################################################################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#===================================================================================
#     u p d a t e T i t l e
#===================================================================================

def updateTitle(wave, title):
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # remember or update the title of this wave
  _titles = db.GqlQuery("SELECT * FROM Titles WHERE wave = :1", wave)
  _title = _titles.get()
  if _title == None:
    new_title = Titles()
    new_title.wave = wave
    new_title.title = title
    new_title.put()
  else:
    _title.title = title
    _title.put()

#===================================================================================
#     s h o w M e n u
#===================================================================================

def showMenu(event):
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # insert a menu
  reply = event.blip.reply()
  reply.append("About XMPP Lite \n ")
  reply.range(1, 1+15).annotate('link/manual', 'http://wave-xmpp.appspot.com/public/xmpplite.htm')
  reply.append(element.Button('subscribe', 'Subscribe'))
  reply.append(element.Button('unsubscribe', 'Unsubscribe'))

#===================================================================================
#     O n F o r m B u t t o n C l i c k e d
#===================================================================================

def OnFormButtonClicked(event, wavelet):
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # these are the handlers for the menu above
  wave  = wavelet.wave_id
  title = wavelet.title
  updateTitle(wave, title)
  button = event.button_name
  if button == 'subscribe':
    jid = event.modified_by
    # - - - - - - - - - - - - - - - - - - - - - - - -
    jid = re.sub(r"@googlewave\.com", "@gmail.com", jid)
    # - - - - - - - - - - - - - - - - - - - - - - - -
    xmpp.send_message(jid, _subscribe(jid, wave))
  if button == 'unsubscribe':
    jid = event.modified_by
    # - - - - - - - - - - - - - - - - - - - - - - - -
    jid = re.sub(r"@googlewave\.com", "@gmail.com", jid)
    # - - - - - - - - - - - - - - - - - - - - - - - -
    xmpp.send_message(jid, _unsubscribe(jid, wave))

#===================================================================================
#     O n W a v e l e t S e l f A d d e d
#===================================================================================

def OnWaveletSelfAdded(event, wavelet):
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # just create a menu when this robot is added
  wave  = wavelet.wave_id
  title = wavelet.title
  updateTitle(wave, title)
  showMenu(event)

#===================================================================================
#     O n B l i p S u b m i t t e d
#===================================================================================

def OnBlipSubmitted(event, wavelet):
  wave  = wavelet.wave_id
  title = wavelet.title
  updateTitle(wave, title)
  text = event.blip.text
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # create a menu
  logging.info("found at " + str(text.find('[xmpp_m]')))
  if text.find('[xmpp_m]') == 1:
    showMenu(event)
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # subscribe to this wave
  elif text.find('[xmpp_s]') == 1:
    jid = event.modified_by
    # - - - - - - - - - - - - - - - - - - - - - - - -
    jid = re.sub(r"@googlewave\.com", "@gmail.com", jid)
    # - - - - - - - - - - - - - - - - - - - - - - - -
    text = _subscribe(jid, wave)
    xmpp.send_message(jid, text)
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # unsubscribe from this wave
  elif text.find('[xmpp_u]') == 1:
    jid = event.modified_by
    # - - - - - - - - - - - - - - - - - - - - - - - -
    jid = re.sub(r"@googlewave\.com", "@gmail.com", jid)
    # - - - - - - - - - - - - - - - - - - - - - - - -
    text = _unsubscribe(jid, wave)
    xmpp.send_message(jid, text)
  #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  # this is where we forward the messages to the subscribers
  else:
    text.strip()
    if text != "":
      _subscriptions = db.GqlQuery("SELECT * FROM Subscriptions WHERE wave = :1", wave)
      for _subscription in _subscriptions:
        xmpp.send_message(_subscription.jid, "\n-->" + title + "\n-->" + event.modified_by + "\n" + text)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#######################################################################################################################################################################
#######################################################################################################################################################################
#
#     A  P  P     E  N  G  I  N  E
#
#######################################################################################################################################################################
#######################################################################################################################################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#===================================================================================
#     W e b A b o u t
#===================================================================================

class WebAbout(webapp.RequestHandler):
  def get(self):
    self.redirect('/public/xmpplite.htm')

#===================================================================================
#     W e b A b o u t
#===================================================================================

class WebManage(webapp.RequestHandler):
  def get(self):
    action = self.request.get('action')
    if action == "fix":
      self.redirect('/public/xmpplite.htm')
      '''
      _subscriptions = db.GqlQuery("SELECT * FROM Subscriptions")
      for _subscription in _subscriptions:
        old = _subscription.jid
        if re.search(r"@googlewave\.com", old):
          self.response.out.write("Found " + old + "<br/>");
          new = re.sub(r"@googlewave\.com", "@gmail.com", old)
          self.response.out.write("Change to " + new + "<hr noshade size='1'>");
          #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
          self.response.out.write("~~~~~~~~~~~~ above<hr noshade size='1'>");
          #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
          _subscription.jid = new
          _subscription.put()
          #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
          _invite(new)
          #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
          # get the title of this subscription
          title = ""
          _waves = db.GqlQuery("SELECT * FROM Titles WHERE wave = :1", _subscription.wave)
          _wave = _waves.get()
          if _wave != None:
            title = "\n-->" + _wave.title
          #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
          xmpp.send_message(new, "\n-->" + title + "\n-->XMPP Administrator\nOk, this should now work. All subscriptions to username@googlewave.com will now be sent to the jid username@gmail.com. (You weren't getting any notifications because they got sent to username@googlewave.com even if you signed up with username@gmail.com)")
          #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      '''
    else:
      self.redirect('/public/xmpplite.htm')

#===================================================================================
#     _ _ m a i n _ _
#===================================================================================

if __name__ == '__main__':
  appHandler = []
  appHandler.append(('/', WebAbout))
  appHandler.append(('/manage', WebManage))
  appHandler.append(('/_ah/xmpp/message/chat/', XMPPHandler))  
  botInstance = robot.Robot('XMPP', image_url='http://wave-xmpp.appspot.com/public/image.png', profile_url='http://wave-xmpp.appspot.com/public/xmpplite.htm')
  botInstance.register_handler(events.WaveletSelfAdded,  OnWaveletSelfAdded)
  botInstance.register_handler(events.BlipSubmitted,     OnBlipSubmitted)
  botInstance.register_handler(events.FormButtonClicked, OnFormButtonClicked)
  appengine_robot_runner.run(botInstance, debug=True)
