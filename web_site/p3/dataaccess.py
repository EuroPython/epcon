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
        if p3p.image_gravatar:
            image = utils.gravatar(profile['email'])
        elif p3p.image_url:
            image = p3p.image_url
        else:
            image = profile['image']
        profile.update({
            'interests': [ t.name for t in p3p.interests.all() ],
            'twitter': p3p.twitter,
            'image': image,
            'image_gravatar': p3p.image_gravatar,
            'image_url': p3p.image_url,
        })
    return profile

profile_data = cache_me(
    signals=(cdata.profile_data.invalidated,),
    key='profile:%(uid)s')(profile_data, lambda sender, **kw: None)
