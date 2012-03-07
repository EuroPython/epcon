# -*- coding: UTF-8 -*-
from conference import cachef
from conference import dataaccess as cdata
from p3 import models
from p3 import utils

cache_me = cachef.CacheFunction(prefix='p3:')

def profile_data(uid):
    profile = cdata.profile_data(uid)
    try:
        p3p = models.P3Profile.objects\
            .get(profile=uid)
    except models.P3Profile.DoesNotExist:
        pass
    else:
        profile.update({
            'interests': [ t.name for t in p3p.interests.all() ],
            'twitter': p3p.twitter,
            'image': p3p.image_url(),
            'image_gravatar': p3p.image_gravatar,
            'image_url': p3p.image_url(),
            'spam_recruiting': p3p.spam_recruiting,
            'spam_user_message': p3p.spam_user_message,
            'spam_sms': p3p.spam_sms,
        })
    return profile

def _i_profile_data(sender, **kw):
    # l'invalidazione tramite segnale viene gestita da cachef
    return 'profile:%s' % (kw['instance'].profile_id,)

profile_data = cache_me(
    signals=(cdata.profile_data.invalidated,),
    models=(models.P3Profile,),
    key='profile:%(uid)s')(profile_data, _i_profile_data)
