Rows in the clean dataset have been removed, added or modified.  
The verification task dataset was not modified at these positions, but it might need to be.  
{%- if modified_rows_count > 0 -%}
<br>
{{ modified_rows_count }} modified.  
{% endif %}
❗This needs your attention❗
{#  #}
{%- if new_rows_table is defined -%}
### The following rows have been added:
{{ new_rows_table }}
{% endif %}
{#  #}
{%- if removed_rows_table is defined -%}
### The following rows have been removed:
{{ removed_rows_table }}
{% endif %}
