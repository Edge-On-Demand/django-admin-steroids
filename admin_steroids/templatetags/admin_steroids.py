import re

from django import template
from django.template import (
    Variable,
)

register = template.Library()

class SetVarNode(template.Node):
    def __init__(self, new_val, var_name, is_literal=True):
        self.new_val = new_val
        self.var_name = var_name
        self.is_literal = is_literal
    def render(self, context):
        if self.is_literal:
            context[self.var_name] = self.new_val
        else:
            context[self.var_name] = Variable(self.new_val).resolve(context)
        return ''

@register.tag
def setvar(parser, token):
    # This version uses a regular expression to parse tag contents.
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires arguments" % token.contents.split()[0])
    m = re.search(r'(.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError(
            "%r tag had invalid arguments" % tag_name)
    new_val, var_name = m.groups()
    if not (new_val[0] == new_val[-1] and new_val[0] in ('"', "'")):
        is_literal = False
    else:
        new_val = new_val[1:-1]
        is_literal = True
    return SetVarNode(new_val, var_name, is_literal)
