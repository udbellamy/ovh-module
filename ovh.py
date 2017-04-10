#!/usr/bin/python
# -*- coding: utf-8 -*-

import hashlib
import json
import sys
import time

from ansible.module_utils.basic import AnsibleModule

import requests

# On commence par déclarer les options que l'on veut passer au module ansible
fields = {
    "action": {"required": True, "type": "str"},
    "service": {"required": True, "type": "str"},
    "appkey": {"required": True, "type": "str"},
    "consumerkey": {"required": True, "type": "str"},
    "appsecret": {"required": True, "type": "str"},
    "ssh_keys": {"required": False, "type": "list"}
}

module = AnsibleModule(argument_spec=fields)

# On récupère les valeurs de chaque option
action = module.params['action']
service = module.params['service']
appkey = module.params['appkey']
consumerkey = module.params['consumerkey']
appsecret = module.params['appsecret']
ssh_keys = module.params['ssh_keys']

# On récupère la liste des SSH keys au format adéquat
ssh_keys = json.dumps(ssh_keys)

# On récupère la date à de suite maintenant
now = str(int(time.time()))

# On déclare le body et la signature
body = ''
signature = ''

# On déclare les headers simples pour la requête api
headers = {
    'X-Ovh-Application': "%s" % (appkey),
    'X-Ovh-Timestamp': "%s" % (now),
    'X-Ovh-Consumer': "%s" % (consumerkey)
}

# On déclare le type de body
headers['Content-type'] = 'application/json'

# On entre dans la boucle si l'action demandée est reinstall
if "reinstall" in action:
    # Méthode GET pour récupérer l'id de la distribution à réinstaller
    method = "GET"
    target = "https://eu.api.ovh.com/1.0/vps/%s/distribution" % (service)
    # A transformer en fonction, join de la signature et hash
    signature = "+".join([
        appsecret, consumerkey,
        method, target,
        body,
        now
    ]).encode('utf-8')
    # On hash la signature au format sha1
    signature = hashlib.sha1(signature)
    # On déclare le header pour la signature en terminant de la formater
    # comme il faut
    headers['X-Ovh-Signature'] = "$1$" + signature.hexdigest()
    # On exec la requête et on la store dans r
    r = requests.get(target, headers=headers, data=body)
    # On dump la réponse au format json et on la store dans out
    out = json.loads(r.text)
    # On récupère le template_id
    template_id = out["id"]
    # On prépare la demande de reinstall
    method = "POST"
    target = "https://eu.api.ovh.com/1.0/vps/%s/reinstall" % (service)
    # On formate le body avec le template id et la list des ssh key
    body = '{"language":"en","templateId":"%s","sshKey":%s}' % (
        template_id,
        ssh_keys
    )
    # Ceci sera VRAIMENT à transformer en fonction
    signature = "+".join([
        appsecret, consumerkey,
        method, target,
        body,
        now
    ]).encode('utf-8')
    # On hash la signature au format sha1
    signature = hashlib.sha1(signature)
    # On déclare le header pour la signature en terminant de la formater
    # comme il faut
    headers['X-Ovh-Signature'] = "$1$" + signature.hexdigest()
    # On exécute la requête de reinstall
    r = requests.post(target, headers=headers, data=body)
    # On récupère la réponse
    out = json.loads(r.text)
    # On a une réponse "message" si quelque chose ne marche pas
    if "message" in out:
        msg = out["message"]
    # On renvoie un json à ansible indiquant qu'il n'y a eu aucun changement si
    # on détecte dans la réponse que le reinstall n'a pas été fait car il y a
    # déjà trop d'actions en cours
    # + code retour failed
        if "already" in msg:
            print json.dumps({
                "failed": True,
                "action": "Too many actions already occuring"
            })
            sys.exit(1)
    # On récupère le contenu du champ state
    state = out["state"]
    # todo est la valeur attendue pour le champ state, on traite le cas et
    # on renvoie à Ansible un json indiquant que le changement a eu lieu
    # + code retour ok
    if state == "todo":
        print json.dumps({
            "changed": True,
            "action": "%s" % action
        })
    sys.exit(0)
    # On récupère le code retour de la requête api, s'il est différent de 200
    # on renvoie un json à ansible indiquant que l'action a échoué
    # + code retour erreur
    if r.status_code != 200:
        print json.dumps({
            "failed": True,
            "msg": "Failed"
        })
    sys.exit(1)

# On entre dnas la boucle suivante si les actions demandées
# sont start ou stop
if "start" or "stop" in action:
    # On prépare la requête
    target = "https://eu.api.ovh.com/1.0/vps/%s/%s" % (service, action)
    method = "POST"
    # Ma parole va falloir faire une fonction...
    signature = "+".join([
        appsecret, consumerkey,
        method, target,
        body,
        now
    ]).encode('utf-8')
    # On hash la signature au format sha1
    signature = hashlib.sha1(signature)
    # On déclare le header pour la signature en terminant de la formater
    # comme il faut
    headers['X-Ovh-Signature'] = "$1$" + signature.hexdigest()
    # On exécute la requête API et on store le résultat dans la variable r
    r = requests.post(target, headers=headers, data=body)

    # On charge la réponse json dans la variable out. A savoir, le r.json
    # ne donne pas le résultat escompté pour la suite,
    # bug avec if "bidule" in out
    out = json.loads(r.text)

    # Si le service est déjà à l'état attendu ou en cas de souci,
    # le json renvoyé n'a pas de champ "state" mais un champ "message".
    # On traite le cas de figure
    if "message" in out:
        msg = out["message"]
    # On renvoie un json à ansible indiquant que l'action a échoué si
    # on détecte dans la réponse que le service n'existe pas
    # + code retour erreur
        if "exist" in msg:
            print json.dumps({
                "failed": True,
                "msg": "Service %s does not exists" % service
            })
            sys.exit(1)
    # On renvoie un json à ansible indiquant qu'il n'y a eu aucun changement si
    # on détecte dans la réponse que le service est déjà à l'état attendu
    # + code retour ok
        elif "already" in msg:
            print json.dumps({
                "changed": False,
                "action": "%s" % action
            })
            sys.exit(0)
    # On récupère le contenu du champ state
    state = out["state"]
    # todo est la valeur attendue pour le champ state, on traite le cas et
    # on renvoie à Ansible un json indiquant que le changement a eu lieu
    # + code retour ok
    if state == "todo":
        print json.dumps({
            "changed": True,
            "action": "%s" % action
        })
    sys.exit(0)
    # On récupère le code retour de la requête api, s'il est différent de 200
    # on renvoie un json à ansible indiquant que l'action a échoué
    # + code retour erreur
    if r.status_code != 200:
        print json.dumps({
            "failed": True,
            "msg": "Failed"
        })
    sys.exit(1)
