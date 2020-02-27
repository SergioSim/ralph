# browser event logs 

Log when a user sends a (XHR) POST/GET request to the **"/event"** URL

The request should provide **"event_type"**, **"event"**, and **"page"** arguments

Note: browser events are easily indentified by their "event-source": **"browser"**

## Example event:
    {
      "username": "toto",
      "event_source": "browser",
      "name": "page_close",
      "accept_language": "en-US,en;q=0.5",
      "time": "2020-03-02T10:12:08.992343+00:00",
      "agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0",
      "page": "http://localhost:8072/courses/course-v1:universityX+CS111+2020_T1/courseware/5edb208a13004490909da020a9bd115d/cd2bb35541e74e8a8be5d2235d122fd9/",
      "host": "50528a92a868",
      "session": "7c26f91b2debb8fa9df150a823c9b43c",
      "referer": "http://localhost:8072/courses/course-v1:universityX+CS111+2020_T1/courseware/5edb208a13004490909da020a9bd115d/cd2bb35541e74e8a8be5d2235d122fd9/ ",
      "context": {
          "user_id": 2,
          "org_id": "universityX",
          "course_id": "course-v1:universityX+CS111+2020_T1",
          "path": "/event"
      },
      "ip": "172.18.0.1",
      "event": "{}",
      "event_type": "page_close"
    }

### key-value pairs retrieved the same way as in the Server logs:
- username
- accept_language
- time
  - NOTE: fitst called timestamp but then renamed back to time
- agent
- referer
- host
- path
  - always the value "/event"
- context: {user_id, org_id}
- context: {course_id and organisation_id}
  - NOTE: they are retrieved the same way as in the Server logs but instead of extracting the information from the current URI (/event) it uses the URI providen by the **page** argument
- ip

### event_source: value
source track/views/__init__.py
- always present
- always the value "browser"

### name: value & event_type: value
source track/shim
- retrieved from the **event_type** argument
- always a string. But the string could be formatted in different formats (json / URL-encoded notation / "")

### page: value
source track/views/__init__.py
- always present
- retrieved from the **page** argument
- the **page** argument is provided by the javascript front-end and filled with **window.location.href** aka the URL of the current page

### session: value
source track/middleware
- always present
- value retrieved from the md5 encrypted Django session key (with salt "common.djangoapps.trackTrackMiddleware" + SECRET_KEY) from the request or empty string if it isn't found
  - NOTE: this session value is also computed for the Server logs (but removed before it's sent)
    - MD5 is not secure but in the master branch of edx they still use MD5 (why is it important to encrypt the session keys?)
    - session keys are stored in the redis database

### event: value
source track/shim
- retrieved from the **event** argument
  - NOTE: called *data* in code but then renamed back to event

## What triggers the ajax request to the **/event** URL by **"event_type"** and the corresponding **"event"** argument

### event_type: page_close
source common/static/js/src/logger
- triggered when the js event window.onunload is triggered
  - once a page has unloaded (or the browser window has been closed)
  - when the user navigates away from the page (by clicking on a link, submitting a form, closing the browser window, etc.)
  - when a user reloads the page (and the js onload event)
  - NOTE: due to different browser settings, this event may not always work as expected
- **event** is always ""
- method is GET

### event_type: problem_show
source display.coffee (I haven't found which one - but it's probably a compiled version of one of the display.coffee scripts)
and common/lib/xmodule/xmodule/capa_base.py
- triggered when user clicks on the button **"AFFICHER LA REPONSE"** of an CAPA (computer assisted personalized approach) problem
- the **event** argument is composed of one field **{"problem" : value}** where the value is a BlockUsageLocator identifying the course and the occurrence of the defined element in the course
  - The BockUsageLocator stucture is: "block-v1:{course_key}+type@problem+block@{block_id}"
    - where {course_key} is the CourseLocator, EXAMPLE: organization+coursenumber+session
    - where {block_id} is the block_id of the CAPA problem stored in the **edxapp** mongo database **modulestore.structures** collection
  - EXAMPLE: event: {"problem":"block-v1:universityX+CS111+2020_T1+type@problem+block@d0d4a647742943e3951b45d9db8a0ea1"}
- NOTE: the button **"AFFICHER LA REPONSE"** is not always present - it is set by the teacher (always / answered / tried / closed / finished / correct or due date has passed / due date has passed / never present)

### event_type: problem_check
source display.coffee
- triggered when:
  - user clicks on the button **"VALIDER"** of an CAPA problem
  - the problem does not include a file upload
- the **event** argument is a text string in standard URL-encoded notation ("key1=value1&key2=value2")
  - the **keys** are made of 'input_' + block_id + '_' + response_id + '_' + answer_id'
    - where **block_id** is the block_id of the CAPA problem stored in the **edxapp** mongo database **modulestore.structures**
    - response_id >= 2 - (an CAPA problem can have multiple exercices / questions to respond)
    - answer_id >= 1 - **(not understood but guessing)** an exercice of an CAPA problem could have multiple seperate response input fields?
    - NOTE for checkbox problems there is also "%5B%5D" (corresponding to "[]") present after the answer_id
  - the **values** are filled with the user input (for example the indexes of the choosen checkboxes - choice_1 choice_2 .../ the text input etc.)
- NOTE: there are 2 types of events with this event_type - browser / triggered events 
- EXAMPLES: 
  - event: ""
  - event: "input_ae7ef26f168541ac8b341ffef360977f_2_1=userinput"
  - event: "input_f9a0f6e7bff041fb9a0f57acbc6a3714_2_1%5B%5D=choice_1&input_f9a0f6e7bff041fb9a0f57acbc6a3714_2_1%5B%5D=choice_2"

### event_type: problem_graded
source display.coffee
- triggered when:
  - user clicks on the button **"VALIDER"** of an CAPA problem
  - NOTE: then the **problem_check** event is sent
  - then the **problem_check** XHR request '/courses/course-v1:{org}+{course}+{session}/xblock/block-v1:{org}+{course}+{session}+type@problem+block@{bock_id}/handler/xmodule_handler/problem_check' is sent and we recieved a succesful response from the LMS
- the **event** argument is an array of length 2 **[value1, value2]**
  - where the **value1** is filled with the same content as in the previously send problem_check event argument
  - where the **value2** is filled with the context argument of the **problem_check** XHR reuqest
    - the context argument of the **problem_check** XHR reuqest contains the updated rendered html of the CAPA problem which is then show to the user
- EXAMPLE: ["input_becb9c3555c54213b04437c6ebeb01cf_2_1=choice_germany", "\n\n\n<h2 class=\"problem-header\">\n  Checkboxes\n</h2>..."]

### event_type: problem_reset
source capa/display.coffee
- triggered when:
  - user clicks on the button **"REINITIALISER"** on an CAPA problem
- the **event** argument is filled the same way as in the problem_check event - with the values of the user inputs - which the user intends to reset
- NOTE: the button **"REINITIALISER"** is not always present - only in case it is set by the teacher (always / never present)

### event_type: problem_save
source display.coffee
- triggered when:
  - user clicks on the button **"ENREGISTRER"** on an CAPA problem
- the **event** argument is filled the same way as in the problem_check event - with the values of the user inputs - which the user intends save
- NOTE: the button **"ENREGISTRER"** is not always present - only if the teacher limits the number of submissions.

### event_type: seq_goto
source sequence/display.coffee
- triggered when:
  - user clicks on a sequence unit of the sequence navigation bar in a courseware page (to navigate to that sequence unit)
- the **event** argument is filled with a dictionnary {old: value, new: value, id: value}
  - old: value is the current sequece unit id
  - new: value is the next sequence unit id the user intends to navigate to
  - id: value is the BlockUsageLocator identifying the course and the occurrence of the defined sequence in the course
    - EXAMPLE: block-v1:{course_key}+type@sequential+block@{block_id}
- *FUN FACT*: with the server events only we cannot know on which sequence of the course the user lands when he request a course page as the user lands on the last visited sequence of the course. With this event_type we can infer on which sequence the user lands if we look at the last seq_goto of the user.
- *DANGER*: we fist send the browser event and then separatly send the XHR request to the LRS about our intention to navigate, if something goes wrong we can only know from the Runtime Warning logs.

### event_type: seq_next
source sequence/display.coffee
- triggered when the user clicks on the **right** arrow of the sequence navigation bar (to navigate to the **next** sequence unit)
- the **event** argument is filled the same way as in the "event_type: seq_goto" (the value **new** is the value **old** incremented by 1)

### event_type: seq_prev
source sequence/display.coffee
source sequence/display.coffee
- triggered when the user clicks on the **left** arrow of the sequence navigation bar (to navigate to the **previous** sequence unit)
- the **event** argument is filled the same way as in the "event_type: seq_goto" (the value **new** is the value **old** decremented by 1)

## pdf related browser events
source pdf-analytics.js
- those events track user activity on the "manual" pages of the course
  - NOTE: the informations related to the pdf "manuals" are stored in the **edxapp** mongo database 
    - the collection **fs.files** stores their metadata: _id / contentType / locked / chunkSize / content_son (category/name/course/tag/org/revision/run) / filename / displayname / lenght / import_path / uploadDate / thumbnail_location / md5
    - the collection **fs.chunks** stores their binary content: _id / n / data / files_id
    - the collection **modulestore.structures** links the manuals with their corresponding course in the **course** object **pdf_textbooks** array
- they are triggered from the **iframe** of the corresponding pdf document
  - this implies that the **page** argument is filled with the URL of the iframe
    - EXAMPLE: https://www.fun-mooc.fr/courses/course-v1:{course_key}/pdfbook/{book_id}/?viewer=true&file=/asset-v1:{course_key}+type@asset+block/{name_of_the_pdf}.pdf#zoom=page-fit&disableRange=true
      - the **book_id** is the **pdf_textbooks** array index of the corresponding manual
      - the **name_of_the_pdf** corresponds to the original name of the pdf document uploaded by the teacher, its related information is stored in pdf_textbooks[]/chapters/url as "/static/{original_name_of_the_pdf}"
        - *FUN FACT* this implies that if in a course we upload 2 pdf manuals with the same name - the first manual will be overwritten!
- the **event** argument is alwas a string containing a json
  - it contains always 2 common fields **{chapter: value, name: value}**
    - the **chapter** value corresponds to the url of the PDF asset
      - EXAMPLE: /asset-v1:{course_key}+type@asset+block/{name_of_the_pdf}.pdf
      - NOTE: the asset is in public access (no login required)
    - the **name** value is most of the time equal to the event_type value
      - just for event_type: 'book' the **name** value is 'textbook.pdf.page.navigatednext' or 'textbook.pdf.page.loaded' depending on the event
- NOTE: we use PDF.js v1.0.907 to render the pdf manuals

### event_type:	textbook.pdf.thumbnails.toggled
source pdf-analytics.js
- triggered when the user clicks on the **"Toggle sidebar"** icon of the pdf iframe OR on the **Show thumbnails** icon of the sidebar
- the **event** argument is filled with one additional key-value pair: **page: value**
  - the **page** value corresponds to the page number that is currently visible to the user
- EXAMPLE: "{\"page\":1,\"chapter\":\"/asset-v1:{course_key}+type@asset+block/{name_of_the_pdf}.pdf\",\"name\":\"textbook.pdf.thumbnails.toggled\"}"
- WARNING: there is no difference in the event if the user clicks on **"Toggle sidebar"** or **Show thumbnails**

### event_type: textbook.pdf.thumbnail.navigated
source pdf-analytics.js
- triggered when the user clicks on a thumbnail image to navigate to a page of the pdf
- the **event** argument is filled with two additional key-value pairs: **page: value, thumbnail_title: value**
  - the **page** value corresponds to the page number that the user navigated to
  - the **thumbnail_title** value corresponds to the name of the thumbnail the user navigated to
    - NOTE: as we are using PDF.js to render the manual and we support only English/French languages the thumbnail_title should be always 'Page {{page_number}}'
      - source pdf.js/web/thumbnail_view.js function thumbnailView

### event_type: textbook.pdf.outline.toggled
source pdf-analytics.js
- triggered when the user clicks on the outline icon of the sidebar
- the **event** argument is filled with one additional key-value pair: **page: value**
  - the **page** value corresponds to the page number that is currently visible to the user

### event_type: textbook.pdf.chapter.navigated
source lms/static/templates/static_pdfbook.html
- triggered when the user clicks on a manual chapter (on the left of the pdf iframe)
- the **event** argument is filled with one additional key-value pair: chapter_title: value
  - the **chapter_title** corresponds to the chapter title of the manual

### event_type: textbook.pdf.zoom.buttons.changed
source pdf-analytics.js
- triggered when the user clicks on the Zoom In or Zoom Out icon
- the **event** argument is filled with two additional key-value pairs: **page: value, direction: value**
  - the **page** value corresponds to the page number that is currently visible to the user
  - the **direction** value is **"in"** if user Zooms In or **"out"** if user Zooms Out

### event_type: textbook.pdf.zoom.menu.changed
source pdf-analytics.js
- triggered when the user selects a magnification setting.
- the **event** argument is filled with two additional key-value pairs: **page: value, amount: value**
  - the **page** value corresponds to the page number that is currently visible to the user
  - the **amaunt** value corresponds to the choosen scaling ('0.5', '0.75', '1', '1.25', '1.5', '2', '3', '4', 'page-actual', 'auto', 'page-width', 'page-fit')

### event_type textbook.pdf.page.scrolled")
source pdf-analytics.js
- triggered when the user scrolls to the next or previous page using the mousewheel AND the **transition takes less than 50 milliseconds**
  - NOTE: the transition from one page to another happens when the next/previous page takes more display space than the original one
- the **event** argument is filled with two additional key-value pairs: **page: value, direction: value**
  - the **page** value corresponds to the page number that the user navigated to
  - the **direction** value indicates in which direction the user scolled ("up", "down")

### event_type textbook.pdf.page.navigated")
source pdf-analytics.js
- triggered when the user manually enters a page number
- the **event** argument is filled with one additional key-value pair: **page: value**
  - the **page** value corresponds to the page number that the user navigated to

### event_type textbook.pdf.display.scaled")
source pdf-analytics.js
- triggered when the user selects a magnification setting OR zooms in/out the pdf iframe OR at the first page shown.
- the **event** argument is filled with two additional key-value pairs: **page: value, amount: value**
  - the **page** value corresponds to the page number that is currently visible to the user
  - the **amaunt** value corresponds to the choosen scaling (only nummerical values like 0.25, 1, 1.75 etc.)

### event_type: book
source pdf-analytics.js
- NOTE: there are multiple events of type "book" sorted here by the event: {**"name"**: value}
  - event: {"name": **textbook.pdf.page.loaded**}
    - triggered when the first page is shown to the user and each next page navigation (scroll/page jump etc.)
    - the **event** argument is filled with 3 additional key-value pairs **type: "gotopage", old: value, new: value**
      - the **type** value is always "gotopage"
      - the **old** value corresponds to the page number previously shown to the user
      - the **new** value corresponds to the page number that the user navigated to
        - NOTE: when the first page is shown the new and the old value is 1
  - event: {"name": **textbook.pdf.page.navigatednext**}
    - triggered when the user clicks on the next/previous page icon
    - the **event** argument is filled with 2 additional key-value pairs **type: value, new: value**
    - the **type** argument is ("prevpage"/"nextpage") depending if the user navigates to the previous or next page
    - the **new** argument corresponds to the page number the user inteds to navigate to
- the **event** argument is filled with a dictionary {"type": "gotopage", "old": old_page, "new": page}

### event_type: textbook.pdf.search.executed
https://edx.readthedocs.io/projects/devdata/en/stable/internal_data_formats/tracking_logs.html#textbook-pdf-search-executed

### event_type: textbook.pdf.search.highlight.toggled
https://edx.readthedocs.io/projects/devdata/en/stable/internal_data_formats/tracking_logs.html#textbook-pdf-search-highlight-toggled

### event_type: textbook.pdf.search.navigatednext
https://edx.readthedocs.io/projects/devdata/en/stable/internal_data_formats/tracking_logs.html#textbook-pdf-search-navigatednext

### event_type: textbook.pdf.search.casesensitivity.toggled
https://edx.readthedocs.io/projects/devdata/en/stable/internal_data_formats/tracking_logs.html#textbook-pdf-searchcasesensitivity-toggled

## WIP on more browser events

**Video related events**
09_events_bumper_plugin.js
- this.log('edx.video.bumper.loaded');
- this.log('edx.video.bumper.played', {currentTime: this.getCurrentTime()});
- this.log('edx.video.bumper.stopped', {currentTime: this.getCurrentTime()});
- this.log(eventName, info);
- this.log('edx.video.bumper.transcript.menu.shown');
- this.log('edx.video.bumper.transcript.menu.hidden');
- this.log('edx.video.bumper.transcript.shown', {currentTime: this.getCurrentTime()});
- this.log('edx.video.bumper.transcript.hidden', {currentTime: this.getCurrentTime()});
09_events_plugin.js
- this.log('load_video');
- this.log('play_video', {currentTime: this.getCurrentTime()});
- this.log('pause_video', {currentTime: this.getCurrentTime()});
- this.log('stop_video', {currentTime: this.getCurrentTime()});
- this.log(eventName, info);
- this.log('seek_video', {
- this.log('speed_change_video', {
- this.log('video_show_cc_menu');
- this.log('video_hide_cc_menu');
- this.log('show_transcript', {current_time: this.getCurrentTime()});
- this.log('hide_transcript', {current_time: this.getCurrentTime()});
P.S. this.log calls Logger.log

**Team page related evets**
https://openedx.atlassian.net/wiki/display/AN/Teams+Feature+Event+Design
do we use team pages at FUN?

**dashboard/legacy.js**
Logger.log('edx.course.enrollment.upgrade.clicked', [user, course], null);

**search_item_view.js**
Logger.log('edx.course.search.result_selected', { 'search_term': searchTerm, 'result_position': (page * pageSize + index), 'result_link': target

**account_settings_factory.js**
Logger.log('edx.user.settings.viewed', { page: "account", visibility: null, user_id: accountUserId });

**learner_profile_factory.js**
Logger.log('edx.user.settings.viewed', { page: "profile", visibility: getProfileVisibility(), user_id: options.profile_user_id });