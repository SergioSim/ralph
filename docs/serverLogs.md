# Server logs
Log events related to server requests

On each page request they are logged if it is not matching the URL patterns

    TRACKING_IGNORE_URL_PATTERNS = [
      r'^/event', r'^/login', r'^/heartbeat', r'^/segmentio/event', r'^/performance'
    ]

also if URL starts with "/event_logs" and user.is_staff - we don't log

server logs are handled in the middleware layer

## Example event:
    {
        "username": "toto",
        "event_type": "/courses/course-v1:test+CS101+2020_T1/info",
        "ip": "172.18.0.1",
        "agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0",
        "host": "afcfb5c63273",
        "referer": "",
        "accept_language": "en-US,en;q=0.5",
        "event": "{\"POST\": {}, \"GET\": {}}",
        "event_source": "server",
        "context": {
            "course_user_tags": {},
            "user_id": 2,
            "org_id": "test",
            "course_id": "course-v1:test+CS101+2020_T1",
            "path": "/courses/course-v1:test+CS101+2020_T1/info"
        },
        "time": "2020-02-25T12:18:00.612692+00:00",
        "page": null
    }

[username](#username-value) <br>
[event_type](#event_type-value) <br>
[ip](#ip-value) <br>
[agent](#agent-value) <br>
[host](#host-value) <br>
[referer](#referer-value) <br>
[accept_language](#accept_language-value) <br>
[event](#event-post-post_keypost_key_value-get-get_keyget_key_values) <br>
[event_source](#event_source-value) <br>
[context-user_id](#context-user_id-value) <br>
[context-org_id](#context-org_id-value) <br>
[context-course_id](#context-course_id-value) <br>
[context-path](#context-path-value) <br>
[context-course_user_tags](#context-course_user_tags-key-value) <br>
[time](#time-value) <br>
[page](#page-value)

### username: value
source track/views/__init__.py
- always present
- retrieved from **request.user.username** which belongs to the model auth_user table
- it's a **varchar(30)**
- if user not logged in (anonymous) 
  - value = **""**
- if an exception is rised when retrieving the username the value is **"anonymous"***
- *FUN FACT* - what if the username of an user is actually "anonymous" ? 
- NOTE: usernames are made of 2-30 ASCII letters / numbers / underscores (_) / hyphens (-)

### event_type: value
source track/views/__init__.py
- always present
- portion of the URL after the host name
- retrieved from **request.META['PATH_INFO']**

### ip: value
source track/views/__init__.py
- always present
- The IPv4 address of the client.
- First matched public IP if found
- else the first matched non-public IP
- else ""
- retrieved with **get_ip(request)** cf. https://github.com/un33k/django-ipware/tree/1.1.0
- it seems FUN does not support ipv6 ?

### agent: value
source track/views/__init__.py
- always present
- retrieved from the request header 'HTTP_USER_AGENT' aka 'User-Agent'
- empty sting if 'HTTP_USER_AGENT' not present
- NOTE: HTTP_USER_AGENT can carry several pieces of information such as:
  - Browser name and version, Operating System name and version. Default language.

### host: value
source track/views/__init__.py
- always present
- it's the hostname of the server
- in our case, the container ID of the docker container
- EXAMPLE: "afcfb5c63273"

### referer: value
source track/views/__init__.py
- always present
- value from the request header 'HTTP_REFERER' aka 'Referer'
- empty sting if 'HTTP_REFERER' not present
- NOTES: contains the referring url (previous url visited by user)

### accept_language: value
source track/views/__init__.py
- always present
- value from the request header 'HTTP_ACCEPT_LANGUAGE' aka 'Accept-Language'
- empty sting if 'HTTP_ACCEPT_LANGUAGE' not present
- NOTE: contains default language setting of the user

### event: "{\"POST\": {post_key:post_key_value,...}, \"GET\": {get_key:get_key_values,...}"
source track/views/__init__.py
- contains a string of an json object with 2 key value pairs POST and GET filled with content from the http POST request, http GET reques
- keys like ['password', 'newpassword', 'new_password', 'oldpassword', 'old_password', 'new_password1', 'new_password2'] are filtered out
- **DANGER: The "string" is truncated at 500 characters resulting in unparsable (unfinished) json if the content exceedes 500 characters**

### event_source: value
source track/views/__init__.py
- always present
- always the value "server"

### context: {user_id: value}
source common.track.middleware
the private key aka the id of the authenticated user - int [-2147483648:2147483647]

### context: {org_id: value}
source common.track.middleware
- The name of the organization sponsoring the course
- should only contain ascii characters

### context: {course_id: value} 
source UserTagsEventContextMiddleware
- present on each tracking log, populated if user enters a courses page
- if URI regex matches ^.*?/courses/?P **<course_id>**[^/+]+(/|\+)[^/+]+(/|\+)[^/?]+'
    - the value is retrieved from the regex group **<course_id>**
    - = [any string except "/" and "+"] ["/" or "+"] [any string except "/" and "+"] ["/" or "+"] [any string except "/" and "?"]
- if user not logged in (anonymous user)
    - same principe, but "usually" anonymous users are redirected away from courses cf. "courseware.middleware.RedirectUnenrolledMiddleware"
- else
   the value = ""
- NOTE: But then this value is updated in track.context.course_context_from_url:
    - same principe as above but instead of opaque_keys.edx.keys.CourseKey, opaque_keys.edx.locations.SlashSeparatedCourseKey is used to double check and retrieve the course_id value

### context: {path: value}
source source common.track.middleware
- the value is retrieved the same way as [event_type](#event_type-value)
- P.S. instead of request.META['PATH_INFO'], request.META.get('PATH_INFO', '') is used

### context: {course_user_tags: {key: value}}
source UserTagsEventContextMiddleware
- Only present in the logs if a course page is requested (URI matches regex seen above)
- In code explained as:
  - per-course user tags, to be used by various things that want to store tags about the user.
  - Added initially to store assignment to experimental groups.
- DOES AN SQL QUERRY if user authenticated and on a course page:

        SELECT  `user_api_usercoursetag`.`id`, 
                `user_api_usercoursetag`.`user_id`, 
                `user_api_usercoursetag`.`key`, 
                `user_api_usercoursetag`.`course_id`, 
                `user_api_usercoursetag`.`value` 
        FROM `user_api_usercoursetag` 
        WHERE (`user_api_usercoursetag`.`course_id` = course-v1:test+CS101+2020_T1 AND `user_api_usercoursetag`.`user_id` = 2)
- For INFO -> SHOW columns FROM user_api_usercoursetag;

        +-----------+--------------+------+-----+---------+----------------+
        | Field     | Type         | Null | Key | Default | Extra          |
        +-----------+--------------+------+-----+---------+----------------+
        | id        | int(11)      | NO   | PRI | NULL    | auto_increment |
        | key       | varchar(255) | NO   | MUL | NULL    |                |
        | course_id | varchar(255) | NO   | MUL | NULL    |                |
        | value     | longtext     | NO   |     | NULL    |                |
        | user_id   | int(11)      | NO   | MUL | NULL    |                |
        +-----------+--------------+------+-----+---------+----------------+
- if it finds **THE** record (todo: find out where it's inserted...) 
  - it inserts the key-value pair: "course_user_tags": {"some_retrieved_**key**": "some_retrieved_**value**"}
    - some_retrieved_key is an varchar(255) and some_retrieved_value is an longtext (4,294,967,295 or 4GB of characters) 
    - INFO: special characters are getting escaped {"\"": "\""}
- else
  - course_user_tags: {}
- **DANGER: Tracking logs are truncated at TRACK_MAX_EVENT = 50000 < mysql longtext!**

### time: value
source track/views/__init__.py
- always present
- it's the current UTC time
- retrieved with **datetime.datetime.utcnow()**
- EXAMPLE: "2020-02-27T08:39:23.199287+00:00"

### page: value
source track/views/__init__.py
- always present
- always the value null

### Additionnal Information
- "event_source": "browser" events are not related to the track.middleware
- *FUN FACT* about context: values
  - First **those** fields are filled in track.middleware.enter_request_context() and then they are removed in track.shim because of "dublication". **Why are they filled in the first place?**:

        CONTEXT_FIELDS_TO_INCLUDE = [
          'username', *The username of the logged in user*
          'session', *The Django session key that identifies the user's session*
          'ip', *The IP address of the client*
          'agent', *The client browser identification string*
          'host', *The "SERVER_NAME" header, which should be the name of the server running this code*
          'referer',
          'accept_language'
        ]
    - also the field *client_id* is removed : citing comment in code: "This field is only used for Segment web analytics and does not concern researchers"

## Proposed xApi Conversion:


replacing {{key}} with the value of the event[key] value

to select only this type of server event we could use: <br>
&emsp;{{event_source}} == "server" && <br>
&emsp;{{page}} == null && <br>
&emsp;{{event_type}} == {{context[path]}}<br>

    {
      "timestamp": {{time}},
      "actor": {
          "account": {
              "name": {{username}},
              "homePage": "http://fun-mooc.fr"
          },
          "objectType": "Agent"
      },
      "verb": {
          "id": "http://adlnet.gov/expapi/verbs/launched",
          "display": {
              "en-US": "launched"
          }
      },
      "object": {
          "id": "http://fun-mooc.fr/{{event_type}}",
          "definition": {
            "type": "http://activitystrea.ms/schema/1.0/page",
            "name": {
              "en-US": "page"
              }
          },
          "objectType": "Activity"
      },
      "context": {
        "platform" : "http://fun-mooc.fr"
        "extensions": {
          //provide context to the core experience
          "http://fun-mooc.fr/extension/ip": {{ip}},
          "http://fun-mooc.fr/extension/agent": {{agent}},
          "http://fun-mooc.fr/extension/host": {{host}},
          "http://fun-mooc.fr/extension/referer": {{referer}},
          "http://fun-mooc.fr/extension/accept_language": {{accept_language}},
          "http://fun-mooc.fr/extension/course_user_tags": {{context[course_user_tags]}},
          "http://fun-mooc.fr/extension/user_id": {{context[user_id]}},
          "http://fun-mooc.fr/extension/org_id": {{context[org_id]}},
          "http://fun-mooc.fr/extension/course_id": {{context[course_id]}},
          "http://fun-mooc.fr/extension/server/event": {{event}}
        }
      }
    }

### additional thoughts
- we could transform the event[event] string into an object (if it is not truncated):
  - "event": "{\"POST\": {}, \"GET\": {}}" => "event": {"POST": {}, "GET": {}},
