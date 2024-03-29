#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2012 WikiEvidens <http://code.google.com/p/wikievidens/>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re

import numpy
import pylab

def graphUserMessages(self, cursor=None):
    """ user who talk each other """
    #fix como evitar que alguien que edita varias veces seguidas (corrigiendo typos) en poco tiempo contabilice como varios mensajes? mejor un mensaje = editado en 1 día?
    #descartar mensajes enviados por IPs ?
    #descartar ediciones en la página de uno mismo? pueden ser respuestas, algunos usuarios no responden en la página del destinatario sino en la propia
    #mejoras: colorear los usuarios que reciben más mensajes (son más importantes en la comunidad), trazos más gruesos, colores, formas de los nodos...
    #filtrar bots? tanto para mensajes como para ediciones
    
    result = cursor.execute("SELECT rev_user_text, rev_title FROM revision WHERE 1") #fix generalizar usando namespace 3
    messages = {}
    for row in result:
        sender = row[0]
        target = row[1]
        if not re.search(ur'(?im)^(Usuario Discusión|Usuario Conversación|User talk):.+$', target):
            continue
        target = ':'.join(target.split(':')[1:]) #removing namespace prefix
        target = target.split('/')[0] #removing /Archivo 2009, etc
        
        #discarding stuff
        if sender == target:
            continue
        if re.search(ur'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', sender) or re.search(ur'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', target):
            continue
        
        if messages.has_key(sender):
            if messages[sender].has_key(target):
                messages[sender][target] += 1
            else:
                messages[sender][target] = 1
        else:
            messages[sender] = {target: 1}
    
    print messages.items()
    
    output = ''
    for sender, targets in messages.items():
        for target, times in targets.items():
            if times >= 2: #fix limite demasiado bajo? dejar los X nodos más habladores?
                output += '"%s" -> "%s" [label="%s"];\n' % (sender, target, times)
    
    output = 'digraph G {\n size="150,150" \n%s\n}' % (output)
    
    if not os.path.exists('output'):
        os.makedirs('output')
    
    filename = '%s-usermessagesgraph' % (self.wiki)
    f=open('output/%s.dot' % filename, 'w')
    
    print "GENERANDO GRAFO"
    
    f.write(output.encode('utf-8'))
    
    f.close()
    
    os.system('dot output/%s.dot -o output/%s.png -Tpng' % (filename, filename))
    print "GRAFO GUARDADO EN OUTPUT/"

def graphUserEditsNetwork(self, cursor=None):
    """ users who have edited the same articles """
    result = cursor.execute("SELECT DISTINCT rev_user_text, rev_page FROM revision WHERE 1 ORDER BY rev_page ASC")
    
    users = []
    users_dic = {}
    page = ''
    for row in result:
        if page:
            if row[1] != page:
                user1 = users[0]
                for user2 in users[1:]:
                    if users_dic.has_key(user1):
                        if users_dic[user1].has_key(user2):
                            users_dic[user1][user2] += 1
                            continue
                    nothing = True
                    for k, v in users_dic.items():
                        if k == user1 and v.has_key(user2):
                            users_dic[user1][user2] += 1
                            nothing = False
                        elif k == user2 and v.has_key(user1):
                            users_dic[user2][user1] += 1
                            nothing = False
                    if nothing:
                        if users_dic.has_key(user1):
                            users_dic[user1][user2] = 1
                        else:
                            users_dic[user1] = {user2: 1}
                page = row[1]
                users = [row[0]] #reset users list, or process will explode
                continue
        else:
            page = row[1]
        if row[0] not in users:
            users.append(row[0])
    
    #fix add last case (last page)
    
    for degrees in range(2,6): #rango de páginas comunes, 1 es demasiado bajo no?
        output = ''
        for k, v in users_dic.items():
            for k2, v2 in v.items():
                if v2 >= degrees:
                    print k, k2, v2
                    output += '"%s" -> "%s" [label="%s", arrowhead="none"];\n' % (k, k2, v2)
        
        output = 'digraph G {\n size="150,150" \n%s\n}' % (output)
        
        if not os.path.exists('output'):
            os.makedirs('output')
        
        filename = '%s-usereditsnetwork-%d' % (self.wiki, degrees)
        f=open('output/%s.dot' % filename, 'w')
        
        print "GENERANDO GRAFO"
        
        f.write(output.encode('utf-8'))
        
        f.close()
        
        os.system('dot output/%s.dot -o output/%s.png -Tpng' % (filename, filename))
        print "GRAFO GUARDADO EN OUTPUT/"

def graphPageHistory(self, cursor=None, range='', entity=''):
    """ page history flow chart"""
    
    if not os.path.exists('output'):
        os.makedirs('output')
    
    filename = '%s-pagehistorygraph' % (self.wiki)
    f=open('output/%s.dot' % filename, 'w')
    
    print "GENERANDO GRAFO"
    a = None
    if range == 'page':
        a = cursor.execute("select rev_user_text, rev_id, rev_text_md5, rev_timestamp from revision where rev_page in (select page_id from page where page_title=?) order by rev_timestamp", (entity,))
    
    if not a:
        return
    
    md5s = {}
    relations = []
    previd = ''
    user = ''
    currentid = 'Start'
    for row in a:
        username = row[0]
        revisionid = row[1]
        md5 = row[2]
        timestamp = row[3]
        
        previd = currentid
        user = username
        currentid = revisionid
        if md5s.has_key(md5): #es una reversion
            currentid = md5s[md5]['id']
        else:
            md5s[md5] = {}
            md5s[md5]['id'] = revisionid
            md5s[md5]['user'] = username
        
        relations.append([previd, currentid, user])
    
    output = ''
    c=0
    for id1, id2, user in relations:
        c+=1
        if c!=len(relations):
            output += '"%s" -> "%s" [label="%s"];\n' % (id1, id2, user)
        else:
            output += '"%s" -> "%s" [label="LAST EDIT: %s"];\n' % (id1, id2, user)
    
    output = 'digraph G {\n size="150,150" \n%s\n}' % (output)
    f.write(output.encode('utf-8'))
    
    f.close()
    
    os.system('dot output/%s.dot -o output/%s.png -Tpng' % (filename, filename))
    print "GRAFO GUARDADO EN OUTPUT/"

def graphUserEdits():
    pass
