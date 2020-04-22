# Triggered server logs

For some specific page requests we write additional logs on top of the usual server logs

these logs are handled after the middleware layer

## CAPA problems related request
source common/lib/xmodule/xmodule/capa_base.py

- fields retrieved the same way as in the server logs:
    - username, ip, agent, host, referer, event_source, context, time
    - **accept_language**: retrived the same way as in the server logs **BUT**:
        - server logs are at the track.middleware.TrackMiddleware level
        - after that - the dark_lang.middleware.DarkLangMiddleware can change or remove the request.META[`HTTP_ACCEPT_LANGUAGE`] based on its configuration
        - and then we process the triggered event with the modified / removed accept_language
- **page** field always "x_module"

- common fields:
    - context : **module**: { **"usage_key"**: value, **"display_name"**: value}
        - the **usage_key** corresponds to the key location of the problem block
        - the **display_name** corresponds to the **fields.dispay_name** of the problem block
    EXAMPLE (ommiting common server fields / specific to triggered event fields):
```json
{
    "context": {
            "module": {
                "usage_key": "block-v1:organisationducours+numeroducours+sessionducours+type@problem+block@da9c3b1ca605401a85542d1b3c01159b",
                "display_name": "Text Input with Hints and Feedback"
            }
        },
}
```
- optional common fields (For blocks that are inherited from a content library (source module_renderer.py)):
    - context : **module**: { **"original_usage_key"**: value, **"original_usage_version"**: value}

### When the user click on a hint button
source function get_demand_hint
- URL: /courses/course-v1:{course_key}/xblock/block-v1:{course_key}+type@problem+block@{block_id}/handler/xmodule_handler/**hint_button**

#### **event_type** : "edx.problem.hint.demandhint_displayed"
- **event** - a dictionnary containing:
    - **module_id** - Identifier for the problem component for which the user requested the hint
    - **hint_index** - index of the hint that was displayed to the user. The first hint defined for a problem is identified with hint_index: 0
    - **hint_len** - The total number of hints defined for this problem
    - **hint_text** - The text of the hint that was displayed to the user

- EXAMPLE (ommiting common server fields):
```json
{
    "event_type": "edx.problem.hint.demandhint_displayed",
    "event": {
        "hint_index": 1,
        "module_id": "block-v1:organisationducours+numeroducours+sessionducours+type@problem+block@da9c3b1ca605401a85542d1b3c01159b",
        "hint_text": "Consider all 50 states, not just the continental United States.",
        "hint_len": 2
    }
}
```
#### Proposed xApi Conversion:

to select only this type of event we could use: <br>
&emsp;{{event_type}} == "edx.problem.hint.demandhint_displayed"<br>

Proposed STATEMENT: <br>
**Student** **Interracted** with **Assessment** (usage_key) hint button (event_type) and recieved the **Hint** (event) as a result <br>

```json
{
    "timestamp": "{{time}}",
    "actor": {
        "account": {
            "name": "{{username}}",
            "homePage": "http://fun-mooc.fr"
        },
        "objectType": "Agent"
    },
    "verb": {
        "id": "http://adlnet.gov/expapi/verbs/interacted",
        "display": {
            "en-US": "interacted"
        }
    },
    "object": {
        "id": "http://fun-mooc.fr/xblock/{{context[module[usage_key]]}}/{{event_type}}",
        "definition": {
        "type": "http://adlnet.gov/expapi/activities/assessment",
        "name": {
            "en-us": "Assessment"
            },
        "extensions": {
            // provide additional information defining the Activity
            "http://fun-mooc.fr/extension/path": "{{context[path]}}",
            "http://fun-mooc.fr/extension/module": "{{context[module]}}",
            "http://fun-mooc.fr/extension/event_type": "{{event_type}}",
        }
        },
        "objectType": "Activity"
    },
    "result": {
    "extensions": {
        // elements related to the outcome
        "http://fun-mooc.fr/extension/{{event_type}}/event": "{{event}}"
    }
    },
    "context": {
        "platform" : "http://fun-mooc.fr",
        "extensions": {
            //provide context to the core experience
            "http://fun-mooc.fr/extension/ip": "{{ip}}",
            "http://fun-mooc.fr/extension/agent": "{{agent}}",
            "http://fun-mooc.fr/extension/host": "{{host}}",
            "http://fun-mooc.fr/extension/referer": "{{referer}}",
            "http://fun-mooc.fr/extension/accept_language": "{{accept_language}}",
            "http://fun-mooc.fr/extension/org_id": "{{context[org_id]}}",
            "http://fun-mooc.fr/extension/course_id": "{{context[course_id]}}",
            "http://fun-mooc.fr/extension/course_user_tags": "{{context[course_user_tags]}}",
            "http://fun-mooc.fr/extension/user_id": "{{context[user_id]}}",
        }
    }
}
```
### When the user clicks on the submit button
- URL: /courses/course-v1:{course_key}/xblock/block-v1:{course_key}+type@problem+block@{block_id}/handler/xmodule_handler/**problem_check**
- beside the server event capturing the content of the POST request and the browser events "**problem_check**"/"**problem_graded**" additionnal events are triggered:
    - if the student is not allowed to submit the answer (exceded max_attempts / submitted to late - past this problem's due date) OR
    - if the problem has to be reset / randomized before resubmiting but student sends same response without reseting / randomizing the problem:
        - (The last one seems to be not allowed by the front-end but it protects against people capturing the last request sent and resending it)
        - we trigger **problem_check_fail** event
    - else:
        - we trigger **problem_check** event
        - if the problem include feedback messages we also trigger **edx.problem.hint.feedback_displayed** event

#### **event_type**: "problem_check"
- **event** - a dictionnary containing:
    - **state** - a dictionnary containing information extracted from the **courseware_studentmodule** table where the previous state of each problem / course / chapter / etc. is saved:
        - **seed** - the value depends on the problem randomization setting:
            - 1 - if randomization is set to NEVER (source capa_base.py)
            - one of 0:19 - if randomization is set to PER_STUDENT: seed = one of 0:(NUM_RANDOMIZATION_BINS-1) (source capa_base.py)
            - one of 0:999 - if else: seed = one of 0:(MAX_RANDOMIZATION_BINS-1) (source capa_base.py)
            - *FUN FACT* the last number is generated by (one of -2147483648:2147483648) % 1000 - the distibution might be very slightly inclined towards values between 0:648
        - **student_answers** - a dictionnary
            - {} - empty dictionnary - if the problem is submitted the first time OR was reset the previous time
            - a dictionnary of key:value pairs corresponding to the students previous responses:
                - the **keys** are made of block_id + `_` + response_id + `_` + answer_id (see problem_check of browser events)
                - the **values** are filled with the corresponding user input (string) / name of the choosen single choice option OR an array of choices for multichoice questions
        - **correct_map** - a dictionnary:
            - {} - empty dict - if the problem is submitted the first time OR was reset the previous time
            - else - a dictionnary containing for each each problem ID (block_id + `_` + response_id + `_` + answer_id) key the following dictionnary:
                - **correctness** - `correct`, `incorrect`, or `partially-correct`
                - **npoints** - null, or integer specifying number of points awarded for this answer_id
                - **msg** - string (may have HTML) giving extra message response (displayed below textline or textbox)
                - **hint** - string (may have HTML) giving optional hint (displayed below textline or textbox, above msg)
                - **hintmode** - one of (null,`on_request`, `always`) criteria for displaying hint
                - **queuestate** - Dict {key:'', time:''} where key is a secret string, and time is a string dump of a DateTime object in the format `%Y%m%d%H%M%S`. Is null when not queued
                - **answervariable**
                    - for dropdown problems is filled with the script processor context value of the key matching the student response value
                        - *FUN_FACT* EXAMPLE: if the dropdown problem has a response value `1` and the randomization setting is set to `NEVER` the context `seed` value matches the student response value and the answervariable=`$seed`
        - **input_state** - a dictionnary of key:value pairs:
                - the **keys** are made of block_id + `_` + response_id + `_` + answer_id (see problem_check of browser events)
                - the **values** are always empty dictionnaries {} (but NOT 100% sure...)
            - the dictionnary can have more keys for matlab inputs see -> common/lib/capa/capa/inputtypes.py MatlabInput (queuestate, queue_msg, queuekey, queuetime)
        - **done** - the value depends on the previous student action
            - null - if the problem is submitted the first time
            - true - if the problem is submitted a subsequent time
            - false - if the problem was reset the previous time
    - **correct_map** - as state.correct_map but contains the information for the current submission (not the previous one)
    - **success** - `incorrect`, `correct` (correct even if paritally correct)
    - **problem_id** - ID of the problem that was checked EXAMPLE: u`block-v1:{course_key}+type@problem+block@{block_id}` (same as sontext[module[usage_key]])
    - **grade** - Current grade value
    - **max_grade** - Maximum possible grade value
        - QUESTION: max_grade is computed with the sum of the correct_map.problemIDs.npoints - but on all my tests npoints is null (event when the problem weight is set in the studio)
    - **answers** - a dictionnary of key:value pairs:
        - the **keys** are made of block_id + `_` + response_id + `_` + answer_id (see problem_check of browser events)
        - the **values** are filled with the corresponding user input (string) / name of the choosen single choice option OR an array of choices for multichoice questions 
    - **attempts** - The number of times the user attempted to answer the problem.
    - **submission** - a dictionnary containing for each problem ID key the following dictionnary:
        - **question** (str): Is the prompt that was presented to the student.  It corresponds to the label of the input.
        - **answer** (mixed): Is the answer the student provided. This may be a rich structure
            - for single/multi-choice questions the answer is converted to the user visible answer: EXAMPLE: from `choice_1` to `Indonesia`
        - **response_type** (str): The XML tag of the capa response type. One of [`javascriptresponse`, `choiceresponse`, `multiplechoiceresponse`, `truefalseresponse`, `optionresponse`, `numericalresponse`, `stringresponse`, `customresponse`, `symbolicresponse`, `coderesponse`, `externalresponse`, `formularesponse`, `schematicresponse`, `imageresponse`, `annotationresponse`, `choicetextresponse`] source (responsetypes.py)
        - **input_type** (str): The XML tag of the capa input type. One of [`optioninput`, `choicegroup`, `radiogroup`, `checkboxgroup`, `javascriptinput`, `jsinput`, `textline`, `filesubmission`, `codeinput`, `textbox`, `matlabinput`, `schematic`, `imageinput`, `crystallography`, `vsepr_input`, `chemicalequationinput`, `formulaequationinput`, `drag_and_drop_input`, `editamoleculeinput`, `designprotein2dinput`, `editageneinput`, `annotationinput`, `radiotextgroup`, `checkboxtextgroup`] source (inputtypes.py)
        - **correct** (bool): Whether or not the provided answer is correct.  Will be an empty string if correctness could not be determined.
        - **variant** (str): empty string if randomization is set to NEVER - else: the corresponding randomization `seed` value.

        - EXAMPLE (ommiting common server/triggered fields)
```json
{
    "event_type": "problem_check",
        "event": {
            "submission": {
                "da9c3b1ca605401a85542d1b3c01159b_2_1": {
                    "input_type": "textline",
                    "question": "Which U.S. state has the largest land area?",
                    "response_type": "stringresponse",
                    "answer": "Texas",
                    "variant": 923,
                    "correct": false
                },
                "da9c3b1ca605401a85542d1b3c01159b_3_1": {
                    "input_type": "choicegroup",
                    "question": "Which of the following is a vegetable?",
                    "response_type": "multiplechoiceresponse",
                    "answer": "pumpkin <choicehint>A pumpkin is the fertilized ovary of a squash plant and contains seeds, meaning it is a fruit.</choicehint>",
                    "variant": 923,
                    "correct": false
                }
            },
            "success": "incorrect",
            "grade": 0,
            "correct_map": {
                "da9c3b1ca605401a85542d1b3c01159b_2_1": {
                    "hint": "",
                    "hintmode": null,
                    "correctness": "incorrect",
                    "npoints": null,
                    "answervariable": null,
                    "msg": "<div class=\"feedback-hint-incorrect\"><div class=\"hint-label\">Incorrect: </div><div class=\"hint-text\">While many people think Texas is the largest state, it is actually the second largest, with 261,797 square miles.</div></div>",
                    "queuestate": null
                },
                "da9c3b1ca605401a85542d1b3c01159b_3_1": {
                    "hint": "",
                    "hintmode": null,
                    "correctness": "incorrect",
                    "npoints": null,
                    "answervariable": null,
                    "msg": "<div class=\"feedback-hint-incorrect\"><div class=\"hint-label\">Incorrect: </div><div class=\"hint-text\">A pumpkin is the fertilized ovary of a squash plant and contains seeds, meaning it is a fruit.</div></div>",
                    "queuestate": null
                }
            },
            "state": {
                "student_answers": {},
                "seed": 923,
                "done": false,
                "correct_map": {},
                "input_state": {
                    "da9c3b1ca605401a85542d1b3c01159b_2_1": {},
                    "da9c3b1ca605401a85542d1b3c01159b_3_1": {}
                }
            },
            "answers": {
                "da9c3b1ca605401a85542d1b3c01159b_2_1": "Texas",
                "da9c3b1ca605401a85542d1b3c01159b_3_1": "choice_1"
            },
            "attempts": 8,
            "max_grade": 2,
            "problem_id": "block-v1:organisationducours+numeroducours+sessionducours+type@problem+block@da9c3b1ca605401a85542d1b3c01159b"
        }
}
```
#### Proposed xApi Conversion:

to select only this type of event we could use: <br>
&emsp;{{event_type}} == "problem_check" && <br>
&emsp;{{page}} == "x_module" && <br>
&emsp;{{event_source}} == "server"<br>

Proposed STATEMENT: <br>
**Student** **Submitted** the **Assessment** (usage_key) by clicking on submit (event_type)  and recieved a **score** (event[grade]), commited the **submission** (event[submission]), incremented the **attempt** count (event[attempts]) etc. as a result <br>
```json
{
    "timestamp": "{{time}}",
    "actor": {
        "account": {
            "name": "{{username}}",
            "homePage": "http://fun-mooc.fr"
        },
        "objectType": "Agent"
    },
    "verb": {
        "id": "http://activitystrea.ms/schema/1.0/submit",
        "display": {
            "en-US": "submitted"
        }
    },
    "object": {
        "id": "http://fun-mooc.fr/xblock/{{context[module[usage_key]]}}/{{event_type}}",
        "definition": {
        "type": "http://adlnet.gov/expapi/activities/assessment",
        "name": {
            "en-us": "Assessment"
            },
        "extensions": {
            // provide additional information defining the Activity
            "http://fun-mooc.fr/extension/path": "{{context[path]}}",
            "http://fun-mooc.fr/extension/module": "{{context[module]}}",
            "http://fun-mooc.fr/extension/event_type": "{{event_type}}",
        }
        },
        "objectType": "Activity"
    },
    "result": {
    "score": {
        "scaled": "{{event[grade]}} / {{event[max_grade]}}",
        "raw": "{{event[grade]}}",
        "min": 0,
        "max": "{{event[max_grade]}}"
    },
    "success": "{{event[success]}}",
    "extensions": {
        // elements related to the outcome
        //### VERSION 1 (filtering out information that is already present)
        "http://fun-mooc.fr/extension/submission": "{{event[submission]}}",
        "http://fun-mooc.fr/extension/correct_map": "{{event[correct_map]}}",
        "http://fun-mooc.fr/extension/state": "{{event[state]}}",
        "http://fun-mooc.fr/extension/answers": "{{event[answers]}}",
        "http://fun-mooc.fr/extension/attempts": "{{event[attempts]}}",
        //### END VERSION 1
        //### VERSION 2 (the easy way, but larger events)
        "http://fun-mooc.fr/extension/{{event_type}}/event": "{{event}}"
        //### END VERSION 2
    }
    },
    "context": {
    "platform": "http://fun-mooc.fr",
    "extensions": {
        // add context to the core experience
        "http://fun-mooc.fr/extension/ip": "{{ip}}",
        "http://fun-mooc.fr/extension/agent": "{{agent}}",
        "http://fun-mooc.fr/extension/host": "{{host}}",
        "http://fun-mooc.fr/extension/referer": "{{referer}}",
        "http://fun-mooc.fr/extension/accept_language": "{{accept_language}}",
        "http://fun-mooc.fr/extension/org_id": "{{context[org_id]}}",
        "http://fun-mooc.fr/extension/course_id": "{{context[course_id]}}",
        "http://fun-mooc.fr/extension/course_user_tags": "{{context[course_user_tags]}}",
        "http://fun-mooc.fr/extension/user_id": "{{context[user_id]}}",
    }
    }
}
```

#### **event_type**: "edx.problem.hint.feedback_displayed" (triggered only for problems including feedback messages)

### event_type: problem_get
NOT A BROWSER EVENT AS  uses url http://localhost:8072/courses/course-v1:{org}+{course}+{session}/xblock/block-v1:{org}+{course}+{session}+type@problem+block@{block_id}/handler/xmodule_handler/**problem_get**

## WIP on "triggered events":
common/djangoapps/student/views.py:511:          track.views.server_track(request, "change-email1-settings", {"receive_emails": "no", "course": course_key.to_deprecated_string()}, page='dashboard')
common/djangoapps/student/views.py:2300:         track.views.server_track(request, "change-email-settings", {"receive_emails": "yes", "course": course_id}, page='dashboard')
common/djangoapps/student/views.py:2309:         track.views.server_track(request, "change-email-settings", {"receive_emails": "no", "course": course_id}, page='dashboard')

common/djangoapps/util/views.py:113:             track.views.server_track(request, 'error:calc', event, page='calc')

common/djangoapps/track/middleware.py:98:        views.server_track(request, request.META['PATH_INFO'], event) (event = {'event-type': 'exception', 'exception': repr(sys.exc_info()[0])})

lms/djangoapps/courseware/module_render.py:120:  track.views.server_track(request, event_type, event, page='x_module')

lms/djangoapps/instructor/views/legacy.py:169:   track.views.server_track(request, "git-pull", {"directory": data_dir}, page="idashboard")
lms/djangoapps/instructor/views/legacy.py:177:   track.views.server_track(request, "reload", {"directory": data_dir}, page="idashboard")
lms/djangoapps/instructor/views/legacy.py:190:   track.views.server_track(request, "list-students", {}, page="idashboard")
lms/djangoapps/instructor/views/legacy.py:197:   track.views.server_track(request, "dump-grades-raw", {}, page="idashboard")
lms/djangoapps/instructor/views/legacy.py:200:   track.views.server_track(request, "dump-grades-csv-raw", {}, page="idashboard")
lms/djangoapps/instructor/views/legacy.py:205:   track.views.server_track(request, "dump-answer-dist-csv", {}, page="idashboard")
lms/djangoapps/instructor/views/legacy.py:547:   track.views.server_track(
lms/djangoapps/instructor/views/legacy.py:558:   track.views.server_track(request, "add-instructor", {"instructor": unicode(user)}, page="idashboard")
lms/djangoapps/instructor/views/legacy.py:588:   track.views.server_track(
lms/djangoapps/instructor/views/legacy.py:599:   track.views.server_track(request, "remove-instructor", {"instructor": unicode(user)}, page="idashboard")

lms/djangoapps/lms_migration/migrate.py:98:      track.views.server_track(request,
lms/djangoapps/lms_migration/migrate.py:111:     track.views.server_track(request, 'reloaded %s now at %s (pid=%s)' % (reload_dir,
lms/djangoapps/lms_migration/migrate.py:228:     track.views.server_track(request, 'reloaded %s' % reload_dir, {}, page='migrate')

lms/djangoapps/dashboard/sysadmin.py:302:        track.views.server_track(request, action, {}, page='user_sysdashboard')
lms/djangoapps/dashboard/sysadmin.py:547:        track.views.server_track(request, action, {},
lms/djangoapps/dashboard/sysadmin.py:649:        track.views.server_track(request, action, {},