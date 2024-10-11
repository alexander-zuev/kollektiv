# Content for item 0

```markdown
[Skip to main content](#__docusaurus_skipToContent_fallback)

Calls Delete
============

POST

/calls/delete
-------------

Calls Delete

Request[​](/reference/service-api/calls-delete-calls-delete-post#request "Direct link to Request")

---------------------------------------------------------------------------------------------------

*   application/json

###

Body

**

required

**

**project\_id** Project Id (string)required

**call\_ids** string\[\]required

**

wb\_user\_id

**

object

Do not set directly. Server will automatically populate this field.

anyOf

*   MOD1

string

Responses[​](/reference/service-api/calls-delete-calls-delete-post#responses "Direct link to Responses")

---------------------------------------------------------------------------------------------------------

*   200
*   422

Successful Response

*   application/json

*   Schema
*   Example (from schema)

**

Schema

**

object

    {}

Validation Error

*   application/json

*   Schema
*   Example (from schema)

**

Schema

**

**

detail

**

object\[\]

*   Array \[\
    \
\
**\
\
loc\
\
**\
\
object\[\]\
\
required\
\
*   Array \[\
    \
\
anyOf\
\
*   MOD1\
*   MOD2\
\
string\
\
integer\
\
*   \]\
    \
\
**msg** Message (string)required\
\
**type** Error Type (string)required\
\
*   \]


    {  "detail": [    {      "loc": [        "string",        0      ],      "msg": "string",      "type": "string"    }  ]}

Loading...
```

----

