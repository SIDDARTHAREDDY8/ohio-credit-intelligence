{#
    Use the custom schema name verbatim (staging / intermediate / public)
    instead of dbt's default "<target>_<custom>" concatenation, so models
    land in the schemas the API and docs expect.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
