from django.apps import apps as global_apps
from django.db import migrations


def forwards_filer_image(apps, schema_editor):
    try:
        CMSPluginFilerImage = apps.get_model('cmsplugin_filer_image', 'FilerImage')
    except LookupError:
        return False

    DjangoCMSPicture = apps.get_model('djangocms_picture', 'Picture')

    for old_obj in CMSPluginFilerImage.objects.all():
        old_cmsplugin_ptr = old_obj.cmsplugin_ptr
        attributes = {}

        if old_obj.alt_text:
            attributes.update({'alt': old_obj.alt_text})

        new_obj = DjangoCMSPicture(
            # template=
            picture=old_obj.image,
            external_picture=old_obj.image_url if old_obj.image_url else '',
            width=old_obj.width,
            height=old_obj.height,
            alignment=old_obj.alignment if old_obj.alignment else '',
            caption_text=old_obj.caption_text,
            attributes=attributes,
            # link_url=
            # link_page=
            # link_target=
            link_attributes=old_obj.link_attributes,
            use_automatic_scaling=old_obj.use_autoscale,
            use_no_cropping=False,
            use_crop=old_obj.crop,
            use_upscale=old_obj.upscale,
            # use_responsive_image=
            thumbnail_options=old_obj.thumbnail_option,
            # Fields from the cms_cmsplugin table
            position=old_cmsplugin_ptr.position,
            language=old_cmsplugin_ptr.language,
            plugin_type='PicturePlugin',
            creation_date=old_cmsplugin_ptr.creation_date,
            changed_date=old_cmsplugin_ptr.changed_date,
            parent=old_cmsplugin_ptr.parent,
            placeholder=old_cmsplugin_ptr.placeholder,
            depth=old_cmsplugin_ptr.depth,
            numchild=old_cmsplugin_ptr.numchild,
            path=old_cmsplugin_ptr.path,
        )
        old_obj.delete()
        new_obj.save()

    return True


def forwards_filer_link(apps, schema_editor):
    try:
        CMSPluginFilerLink = apps.get_model('cmsplugin_filer_link', 'FilerLinkPlugin')
    except LookupError:
        return False

    DjangoCMSLink = apps.get_model('djangocms_link', 'Link')

    for old_obj in CMSPluginFilerLink.objects.all():
        old_cmsplugin_ptr = old_obj.cmsplugin_ptr

        new_obj = DjangoCMSLink(
            # template=
            name=old_obj.name,
            external_link=old_obj.url or '',
            internal_link=old_obj.page_link or None,
            file_link=old_obj.file or None,
            # anchor=
            mailto=old_obj.mailto or '',
            # phone=
            target='_blank' if old_obj.new_window else '',
            attributes=old_obj.link_attributes,
            # Fields from the cms_cmsplugin table
            position=old_cmsplugin_ptr.position,
            language=old_cmsplugin_ptr.language,
            plugin_type='LinkPlugin',
            creation_date=old_cmsplugin_ptr.creation_date,
            changed_date=old_cmsplugin_ptr.changed_date,
            parent=old_cmsplugin_ptr.parent,
            placeholder=old_cmsplugin_ptr.placeholder,
            depth=old_cmsplugin_ptr.depth,
            numchild=old_cmsplugin_ptr.numchild,
            path=old_cmsplugin_ptr.path,
        )
        old_obj.delete()
        new_obj.save()

    return True


def forwards(apps, schema_editor):
    cmsplugin_filer_image = forwards_filer_image(apps, schema_editor)
    cmsplugin_filer_link = forwards_filer_link(apps, schema_editor)

    if not cmsplugin_filer_image and not cmsplugin_filer_link:
        return


class Migration(migrations.Migration):
    """
    Move data from cmsplugin-filer to the new djangocms-* plugins.

    See: https://docs.djangoproject.com/en/1.11/howto/writing-migrations/#migrating-data-between-third-party-apps
    """
    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
    dependencies = [
        ('conference', '0022_alter_sponsorincome_tags'),
        ('djangocms_picture', '0011_auto_20190314_1536'),
        ('djangocms_link', '0015_auto_20190621_0407'),
    ]

    if global_apps.is_installed('cmsplugin_filer_image'):
        dependencies.append(('cmsplugin_filer_image', '0009_auto_20160713_1853'))

    if global_apps.is_installed('cmsplugin_filer_link'):
        dependencies.append(('cmsplugin_filer_link', '0007_auto_20160713_1853'))
