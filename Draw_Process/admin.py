from django.contrib import admin
# Register your models here.

# @admin.register(Export)
# class ExportAdmin(admin.ModelAdmin):
#     list_display = ('id', 'caption', 'author', 'publish_time')

class MyAdmin(admin.ModelAdmin):
    def change_view(self, request, object_id, form_url='', extra_context=None):
        result_template = super(MyAdmin, self).change_view(request, object_id, form_url, extra_context)
        result_template['location'] = 'Draw_Process/index/'
        return result_template

