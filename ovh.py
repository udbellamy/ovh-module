#!/usr/bin/python

import sys
import json
import requests
import time
import hashlib
from ansible.module_utils.basic import *

# On commence par déclarer les options que l'on veut passer au module ansible
fields = {
      "action":                  {"required": True, "type": "str"},
      "sname":                 {"required": True, "type": "str" },
      "appkey":                {"required": True, "type": "str" },
      "consumerkey":       {"required": True, "type": "str" },
      "appsecret":             {"required": True, "type": "str" }
}

module = AnsibleModule(argument_spec=fields)

# On récupère les valeurs de chaque option
actionv = module.params['action']
service = module.params['sname']
appkey = module.params['appkey']
consumerkey = module.params['consumerkey']
appsecret = module.params['appsecret']

# On récupère la date à de suite maintenant
now = str(int(time.time()))

# On set le body à rien, l'url de l'api ovh à laquelle on substitue le nom du servision et l'action à réaliser, enfin la méthode utilisée, qui sera toujours POST pour ce simple module
body = ''
target = "https://eu.api.ovh.com/1.0/vps/%s/%s" % (service, actionv)
method = "POST"

# On génère la signature requise par OVH, concaténation des différentes options en une seule string au format voulu
signature = "+".join([
    appsecret, consumerkey,
    method, target,
    body,
    now
]).encode('utf-8')

# On hash la signature au format sha1
signature = hashlib.sha1(signature)

# On déclare les headers simples pour la requête api
headers = {
            'X-Ovh-Application': "%s" % (appkey),
            'X-Ovh-Timestamp': "%s" % (now),
            'X-Ovh-Consumer': "%s" % (consumerkey)
        }

# On déclare le header pour la signature en terminant de la formater comme il faut
headers['X-Ovh-Signature'] = "$1$" + signature.hexdigest()
# On déclare le type de body (qui est inexistant pour le moment, mais ça pourrait servir par la suite)
headers['Content-type'] = 'application/json'

# On exécute la requête API et on store le résultat dans la variable r
r = requests.post(target, headers=headers, data=body)

# On charge la réponse json dans la variable out. A savoir, le r.json ne donne pas le résultat escompté pour la suite, bug avec if "bidule" in out
out = json.loads(r.text)

# Si le service est déjà à l'état attendu ou en cas de souci, le json renvoyé n'a pas de champ "state" mais un champ "message". On traite le cas de figure
if "message" in out :
    msg = out["message"]
# On renvoie un json à ansible indiquant que l'action a échoué si on détecte dans la réponse que le service n'existe pas + code retour erreur
    if "exist" in msg :
        print json.dumps({
          "failed" : True,
          "msg" : "Service %s does not exists" % service
        })
        sys.exit(1)
# On renvoie un json à ansible indiquant qu'il n'y a eu aucun changement si on détecte dans la réponse que le service est déjà à l'état attendu + code retour ok
    elif "already" in msg :
        print json.dumps({
          "changed" : False,
          "action" : "%s" % actionv
        })
        sys.exit(0)
# On récupère le contenu du champ state
state = out["state"]
# todo est la valeur attendue pour le champ state, on traite le cas et on renvoie à Ansible un json indiquant que le changement a eu lieu + code retour ok
if state == "todo":
    print json.dumps({
      "changed" : True,
      "action" : "%s" % actionv
    })
sys.exit(0)
# On récupère le code retour de la requête api, s'il est différent de 200 on renvoie un json à ansible indiquant que l'action a échoué + code retour erreur
if 200 not in r.status_code:
    print json.dumps({
      "failed" : True,
      "msg" : "Failed"
    })
sys.exit(1)
