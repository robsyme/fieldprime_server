# fpApi.py
# Michael Kirk 2013
# 
#

import os, sys, time
import MySQLdb as mdb
from flask import Flask, request, Response, url_for, render_template, g, make_response
from flask import json, jsonify
from werkzeug import secure_filename
from jinja2 import Environment, FileSystemLoader
from functools import wraps

if __name__ == '__main__':
    import os,sys,inspect
    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    parentdir = os.path.dirname(currentdir)
    sys.path.insert(0,parentdir) 

import dbUtil
import fpTrait
import fp_common.models as models
import fpTrial
from dbUtil import GetTrial, GetTrials, GetSysTraits
from fpUtil import HtmlFieldset, HtmlForm, HtmlButtonLink, HtmlButtonLink2
import fpUtil

import websess

app = Flask(__name__)
try:
    app.config.from_object('fp_web_admin.fpAppConfig')
except ImportError:
    print 'no fpAppConfig found'
    pass

# If env var FPAPI_SETTINGS is set then load configuration from the file it specifies:
app.config.from_envvar('FP_WEB_ADMIN_SETTINGS', silent=True)

# Load the Data Access Layer Module (must be named in the config)
import importlib
dal = importlib.import_module(app.config['DATA_ACCESS_MODULE'])

LOGIN_TIMEOUT = 300            # Idle time before requiring web user to login again


#############################################################################################
###  FUNCTIONS: #############################################################################

def dec_check_session():
#-------------------------------------------------------------------------------------------------
# Decorator to check if in valid session. If not, send the login page.
# Generates function that has session as first parameter.
#
    def param_dec(func):
        @wraps(func)
        def inner(*args, **kwargs):
            COOKIE_NAME = 'sid'
            sid = request.cookies.get(COOKIE_NAME)                                         # Get the session id from cookie (if there)
            sess = websess.WebSess(False, sid, LOGIN_TIMEOUT, app.config['SESS_FILE_DIR']) # Create or get session object
            g.rootUrl = url_for('main') # Set global var g, accessible by templates, to the url for this func
            if not sess.Valid():
                return render_template('login.html', title='Field Prime Login')

            return func(sess, *args, **kwargs)
        return inner
    return param_dec


def CheckPassword(user, password):
#-----------------------------------------------------------------------
# Validate user/password, returning boolean indicating success
#
    try:
        usrname = 'fp_' + user
        usrdb = usrname
        con = mdb.connect('localhost', usrname, password, usrdb);
        cur = con.cursor()
        cur.execute("SELECT VERSION()")
        ver = cur.fetchone()
        return True
    except mdb.Error, e:
        return False


def FrontPage(sess):
#-----------------------------------------------------------------------
# Return HTML Response for main user page after login
#
    sess.resetLastUseTime()

    # Administer passwords button:
    r = "<p>" + HtmlButtonLink("Administer Passwords", "{0}?op=user".format(g.rootUrl))

    # Traits:
    trials = GetTrials(sess)
    trialListHtml = "No trials yet" if len(trials) < 1 else ""
    for t in trials:
        trialListHtml += "<li><a href={0}>{1}</a></li>".format(url_for("showTrial", trialId=t.id), t.name)

    r += HtmlFieldset(HtmlForm(trialListHtml) +  HtmlButtonLink("Create New Trial", g.rootUrl + "?op=newTrial"), "Current Trials")

    # System Traits:
    sysTraits = GetSysTraits(sess)
    #from fp_common.fpTrait import TraitListHtmlTable
    sysTraitListHtml = "No system traits yet" if len(sysTraits) < 1 else fpTrait.TraitListHtmlTable(sysTraits)
    r += HtmlFieldset(HtmlForm(sysTraitListHtml) \
                          + HtmlButtonLink("Create New System Trait", g.rootUrl + "?op=newTrait&tid=sys"),
                      "System Traits")

    return make_response(render_template('genericPage.html', content=r, title="User: " + sess.GetUser()))


def TrialTraitTableHtml(trial):
#----------------------------------------------------------------------------------------------------
    if len(trial.traits) < 1:
        return "No traits configured"
    out = "<table border='1'>"
    out += "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td></tr>".format("Caption", "Description", "Type", "Min", "Max", "Validation")
    for trt in trial.traits:
        out += "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td>".format(
            trt.caption, trt.description, models.TRAIT_TYPE_NAMES[trt.type], trt.min, trt.max)
        if trt.type == 0:
            valOp = '<select name="validationOp">'
            valOp += '<option value="0">Greater Than</option>'
            valOp += '<option value="0">Less Than</option>'
            valOp += '</select>'

            url = url_for('traitValidation', trialId=trial.id, traitId=trt.id,  _external=True)
            validateButton = HtmlButtonLink2("Validation", url) 
            out += "<td>" + validateButton  + "</td>"
    out += "</table>"
    out += "</tr>"
    return out


def TrialHtml(sess, trialId):
#-----------------------------------------------------------------------
# Top level page to display/manage a given trial.
#
    trial = dbUtil.GetTrial(sess, trialId)

    # Trial name and attributes:
    r = "<p><h3>Trial : {0}</h3>".format(trial.name)
    r += "<ul>"
    if trial.site: r += "<li>Site:" + trial.site + "</li>" 
    if trial.year: r += "<li>Year:" + trial.year + "</li>" 
    if trial.site: r += "<li>Acronym:" + trial.acronym + "</li>" 
    r += "</ul>"

    # Attributes:
    attList = dbUtil.GetTrialAttributes(sess, trialId)
    def atts():
        if len(attList) < 1:
            return "No attributes found"
        out = "<ul>"
        for att in attList:
            out += "<li><a href={0}?op=attribute&aid={1}>{2}</a></li>".format(g.rootUrl, att.id, att.name)
        return out + "</ul>"
    r += HtmlForm(HtmlFieldset(atts, "Attributes:"))

    # Traits:
    createTraitButton =  """<p><button style="color: red" onClick="window.location = """
    createTraitButton += """'{0}?op=newTrait&tid={1}'">Create New Trait</button>""".format(g.rootUrl, trialId)
    createTraitButton = '<p>' + fpUtil.HtmlButtonLink2("Create New Trait", "{0}?op=newTrait&tid={1}".format(g.rootUrl, trialId))

    addSysTraitForm = '<FORM method="POST" action="{0}?op=addSysTrait2Trial&tid={1}">'.format(g.rootUrl, trialId)
    addSysTraitForm += '<input type="submit" value="Submit">'
    addSysTraitForm += '<select name="traitID"><option value="0">Select System Trait to add</option>'
    sysTraits = dbUtil.GetSysTraits(sess)
    for st in sysTraits:
        for trt in trial.traits:   # Only add traits not already in trial
            if trt.id == st.id:
                break
        else:
            addSysTraitForm += '<option value="{0}">{1}</option>'.format(st.id, st.caption)
    addSysTraitForm += '</select></form>'
    r += HtmlFieldset(HtmlForm(TrialTraitTableHtml(trial)) + createTraitButton + addSysTraitForm, "Traits:")

    # Trait Instances:
    tiList = dbUtil.GetTraitInstancesForTrial(sess, trialId)
    def tis():
        if len(tiList) < 1:
            return "No trait instances found"
        out = "<ul>"
        for ti in tiList:
            out += "<li><a href={0}?op=traitInstance&tiid={1}>{3}:{2}:{4}</a></li>".format(g.rootUrl, ti.id, ti.trait.caption, ti.trial.name,ti.trial_id)
        return out + "</ul>"
    r += HtmlForm(HtmlFieldset(tis, "Trait Instances:"))

    #============================================================================
    # Download data section:
    #

    # Javascript function to generate the href for the download links.
    # The generated link includes trialId and the user selected output options.
    jscript = """
<script>
function tdSelect() {{
    var tdms = document.getElementById('tdms');
    var out = '{0}?';
    for (var i=0; i<tdms.length; i++)
        if (tdms[i].selected)
          out += '&' + tdms[i].value + '=1';
    return out;
}}
</script>
""".format(url_for("TrialDataHtml", trialId=trialId))
    dl = ""
    dl += jscript
    # Multi select output columns:
    dl += "Select columns to view/download:<br>"
    dl += "<select multiple id='tdms'>";
    dl += "<option value='timestamp' selected='selected'>Timestamps</option>";
    dl += "<option value='user' selected='selected'>User Idents</option>";
    dl += "<option value='gps' selected='selected'>GPS info</option>";
    dl += "<option value='notes' selected='selected'>Notes</option>";
    dl += "<option value='attributes' selected='selected'>Attributes</option>";
    dl += "</select>";
    dl += "<br><a href='dummy' onclick='this.href=tdSelect()'>View tab separated score data (or right click and Save Link As to download)</a>".format(trial.name)
    dl += "<br><a href='dummy' download='{0}.tsv' onclick='this.href=tdSelect()'>Download tab separated score data (browser permitting)</a>".format(trial.name)
    dl += "<br>Note data is TAB separated"
    r += HtmlFieldset(dl, "Score Data:")

    return r


def AddSysTraitTrial(sess, trialId, traitId):
#-----------------------------------------------------------------------
# Return error string, None for success
#
    if traitId == "0":
        return "Select a system trait to add"
    try:
        usrname = 'fp_' + sess.GetUser()
        usrdb = usrname
        qry = "insert into trialTrait (trial_id, trait_id) values ({0}, {1})".format(trialId, traitId)
        con = mdb.connect('localhost', usrname, sess.GetPassword(), usrdb)
        cur = con.cursor()
        cur.execute(qry)
        con.commit()
    except mdb.Error, e:
        return  usrdb + " " + qry
    return None


def AdminForm(sess, op = '', msg = ''):
#-----------------------------------------------------------------------
# Returns Response which is the user admin form. MK - could use template?
#
    adminMsg = msg if op == 'newpw' else ''
    appMsg =  msg if op == 'setAppPassword' else ''
    #adminMsg = op
    #appMsg = msg
    changeAdminPassForm = """
<FORM method="POST" action="{0}?op=newpw">
<p> The <i>Admin Password</i> is the password used to login to this web server to
manage the trials. I.e. the one you must have used at some stage to get to this page.
<p> Enter your login name: <input type="text" name="login">
<p> Enter your current password: <input type=password name="password">
<p>Enter your new password: <input type=password name="newpassword1">
<p>Confirm your new password: <input type=password name="newpassword2">
<p> <input type="submit" value="Change Admin Password">
</FORM>
</form>
{1}
""".format(g.rootUrl, adminMsg)
    changeAppPassForm = """
<FORM method="POST" action="{0}?op=setAppPassword">
<p> The <i>Scoring Devices Password</i> is the password that needs to be configured on the scoring devices
to allow them to download trial information, and upload trial scores. If this is not configured,
or if it is blank, then the scoring devices will be able to download and upload without configuring
a password on the device.
<p> Note this is not the same as the admin password, (used to login to this web server to
manage the trials). The app password is less secure than the admin password (it could be retrieved
from the scoring device with some effort), so this should not be set to the same value as the
admin password.
<p> Enter your <i>Admin</i> login name: <input type="text" name="login">
<p> Enter your current <i>Admin</i> password: <input type=password name="password">
<p>Enter new <i>Scoring Device</i> password: <input type=password name="newpassword1">
<p>Confirm new <i>Scoring Device</i> password: <input type=password name="newpassword2">
<p> <input type="submit" value="Change App Password">
</FORM>
</form>
{1}
""".format(g.rootUrl, appMsg)
    r =  HtmlFieldset(changeAdminPassForm, "Reset Admin password") + \
                    HtmlFieldset(changeAppPassForm, "Reset Scoring Devices Password")
    return render_template('genericPage.html', content=r, title='Field Prime Login')


def ProcessAdminForm(sess, op, form):
#-----------------------------------------------------------------------
# Handle login form submission
# Returns Response for display.
#
    suser = form.get("login")
    password = form.get("password")
    newpassword1 = form.get("newpassword1")
    newpassword2 = form.get("newpassword2")
    if not (suser and password and newpassword1 and newpassword2):
        return AdminForm(sess, op, "<p>Please fill out all fields</p>")
    if newpassword1 != newpassword2:
        return AdminForm(sess, op, "<p>Versions of new password do not match.</p>")
    if not CheckPassword(suser, password):
        return LoginForm("Password is incorrect")

    # OK, all good, change their password:
    try:
        usrname = 'fp_' + suser
        usrdb = usrname
        con = mdb.connect('localhost', usrname, password, usrdb)
        cur = con.cursor()
        if op == 'newpw':
            cur.execute("set password for {0}@localhost = password(\'{1}\')".format(usrname, newpassword1))
            sess.SetUserDetails(suser, newpassword1)
        elif op == 'setAppPassword':
            cur.execute("REPLACE system set name = 'appPassword', value = '{0}'".format(newpassword1))
            con.commit()
        con.close()

        return FrontPage(sess)
    except mdb.Error, e:
        return LoginForm("Password incorrect")  


def LoginForm(msg):
#-----------------------------------------------------------------------
# login form 
    return render_template('login.html', msg = msg, title='Field Prime Login')


# Could put all trait type specific stuff in trait extension classes.
# Aiming for this file to not contain any type specific code.
# class pTrait(models.Trait):
#     def ProcessForm(form):
#         pass

def allowed_file(filename):  # MFK cloned code warning
    ALLOWED_EXTENSIONS = set(['jpg', 'jpeg', 'gif'])
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def NewTraitCategorical(sess, request, newTrait):
    capKeys = [key for key in request.form.keys() if key.startswith("caption_")]
    for key in capKeys:
        caption = request.form.get(key)
        value = request.form.get(key.replace("caption_", "value_"))
        imageURL = None
        imageURLFile = request.files[key.replace("caption_", "imgfile_")]
        if imageURLFile:
            sentFilename = secure_filename(imageURLFile.filename)
            if allowed_file(sentFilename):
                subpath = os.path.join(app.config['CATEGORY_IMAGE_FOLDER'], sess.GetUser(), str(newTrait.id))
                if not os.path.exists(subpath):
                    os.makedirs(subpath)
                imageURLFile.save(subpath +  "/" + sentFilename)
                imageURL = app.config['CATEGORY_IMAGE_URL_BASE'] + sess.GetUser() + "/" + str(newTrait.id) + "/" + sentFilename
            else:
                pass  # should issue a warning perhaps?

        # Add new trait category:
        ncat = models.TraitCategory()
        ncat.value = value
        ncat.caption = caption
        ncat.trait_id = newTrait.id
        ncat.imageURL = imageURL
        sess.DB().add(ncat)

def CreateNewTrait(sess,  trialId, request):
#-----------------------------------------------------------------------
# Create trait in db, from data from html form.
# trialId is id of trial if a local trait, else it is 'sys'.
# Returns error message if there's a problem, else None.
#
    caption = request.form.get("caption")
    description = request.form.get("description")
    type = request.form.get("type")

    # This should be trait type specific (but min, max fields are in trait table):
    min = request.form.get("min")
    max = request.form.get("max")

    sysTrait = True if trialId == "sys" else False
    # We need to check that caption is unique within the trial - for local anyway, or is this at the add to trialTrait stage?
    # For creation of a system trait, there is not an automatic adding to a trial, so the uniqueness-within-trial test
    # can wait til the adding stage.
    dbsess = sess.DB()
    ntrt = models.Trait()
    ntrt.caption = caption
    ntrt.description = description

    # Check for duplicate captions, probably needs to use transactions or something, but this will usually work:
    if not sysTrait: # If local, check there's no other trait local to the trial with the same caption:
        trial = dbUtil.GetTrialFromDBsess(sess, trialId)
        for x in trial.traits:
            if x.caption == caption:
                return 'Error: A local trait with this caption already exists'
        ntrt.trials = [trial]      # Add the trait to the trial (table trialTrait)
        ntrt.sysType = models.SYSTYPE_TRIAL
    else:  # If system trait, check there's no other system trait with same caption:
        sysTraits = dbUtil.GetSysTraits(sess)
        for x in sysTraits:
            if x.caption == caption:
                return 'Error: A system trait with this caption already exists'
        ntrt.sysType = models.SYSTYPE_SYSTEM

    ntrt.type = type
    if min:
        ntrt.min = min
    if max:
        ntrt.max = max

    dbsess.add(ntrt)
    dbsess.commit()

    # Trait type specific processing:
    if int(ntrt.type) == dal.TRAIT_TYPE_TYPE_IDS['Categorical']:
        NewTraitCategorical(sess, request, ntrt)
    elif int(ntrt.type) == dal.TRAIT_TYPE_TYPE_IDS['Integer']:
        pass

    dbsess.add(ntrt)
    dbsess.commit()
    return None


def TraitInstanceHtml(sess, tiId):
#-----------------------------------------------------------------------
# Returns html for data for specified trait instance.
#
    data = sess.DB().query(models.Datum).filter(models.Datum.traitInstance_id == tiId).all()
    r = "Row Column Timestamp numValue textValue<br>"
    for d in data:
        r += "{0} {1} {2} {3} {4}<br>".format(d.trialUnit.row, d.trialUnit.col, d.timestamp, d.numValue, d.txtValue)
    return r


@app.route('/trial/<trialId>/data/', methods=['GET'])
@dec_check_session()
def TrialDataHtml(sess, trialId):
#-----------------------------------------------------------------------
# Returns trial data as plain text csv form - i.e. for download.
# The data is arranged in trial unit rows, and trait instance value and attribute
# columns.
#
    showGps = request.args.get("gps")
    showUser = request.args.get("user")
    showTime = request.args.get("timestamp")
    showNotes = request.args.get("notes")
    showAttributes = request.args.get("attributes")
    SEP = '\t'
    # Get Trait Instances:
    tiList = dbUtil.GetTraitInstancesForTrial(sess, trialId)

    # Work out number of columns for each trait instance:
    numColsPerValue = 1
    if showTime:
        numColsPerValue += 1
    if showUser:
        numColsPerValue += 1
    if showGps:
        numColsPerValue += 2  
    if showNotes:
        numColsPerValue += 1         # MFK NOTE this will need to be removed when we deprecate datum notes    

    # Headers:
    r = "Row" + SEP + "Column"
    if showAttributes:
        trl = dbUtil.GetTrial(sess, trialId)
        for tua in trl.tuAttributes:
            r += SEP + tua.name
    for ti in tiList:
        tiName = "{0}_{1}.{2}.{3}".format(ti.trait.caption, ti.dayCreated, ti.seqNum, ti.sampleNum)
        r += "{1}{0}".format(tiName, SEP)
        if showTime:
            r += "{1}{0}_timestamp".format(tiName, SEP)
        if showUser:
            r += "{1}{0}_user".format(tiName, SEP)
        if showGps:
            r += "{1}{0}_latitude{1}{0}_longitude".format(tiName, SEP)
        if showNotes:
            r += SEP + "{0}.notes".format(tiName)
    if showNotes:
        r += SEP + "Notes"  # Putting notes at end in case some commas slip thru and mess up csv structure
    r += '\n'

    # Data:
    tuList = dbUtil.GetTrialUnits(sess, trialId)
    for tu in tuList:
        # Row and Col:
        r += "{0}{2}{1}".format(tu.row, tu.col, SEP)

        # Attribute Columns:
        if showAttributes:
            for tua in trl.tuAttributes:
                r += SEP
                av = dbUtil.GetAttributeValue(sess, tu.id, tua.id)
                if av is not None:
                    r += av.value

        # Scores:
        for ti in tiList:
            type = ti.trait.type
            datums = dbUtil.GetDatum(sess, tu.id, ti.id)
            if len(datums) == 0:
                r += SEP * numColsPerValue
            else:  # While there might be multiple, we get last:
                # Use the latest:
                lastDatum = datums[0]
                for d in datums:
                    if d.timestamp > lastDatum.timestamp: lastDatum = d
                d = lastDatum
                # This next switch is no good, have to support trait type polymorphism somehow..
                if type == 0: value = d.numValue
                if type == 1: value = d.numValue
                if type == 2: value = d.txtValue
                if type == 3: value = d.numValue
                if type == 4: value = d.numValue
                if type == 5: value = d.txtValue
                r += "{0}{1}".format(SEP, value)
                if showTime:
                    r += "{0}{1}".format(SEP, d.timestamp)
                if showUser:
                    r += "{0}{1}".format(SEP, d.userid)
                if showGps:
                    r += "{0}{1}{0}{2}".format(SEP, d.gps_lat, d.gps_long)
                if showNotes:
                    r += SEP
                    if d.notes != None and len(d.notes) > 0: r += d.notes  ######### MFK move old notes, discontinue support!

        # Notes, as list separated by pipe symbols:
        if showNotes:
            r += SEP + '"'
            tuNotes = dbUtil.GetTrialUnitNotes(sess, tu.id)
            for note in tuNotes:
                r += '{0}|'.format(note.note)
            r += '"'

        # End the line:
        r += "\n"

    return Response(r, content_type='text/plain')


@app.route('/trial/<trialId>', methods=["GET"])
@dec_check_session()
def showTrial(sess, trialId):
#===========================================================================
# Page to display/modify a single trial.
#
    return render_template('genericPage.html', content=TrialHtml(sess, trialId), title='Trial Data')


@app.route('/trial/<trialId>/trait/<traitId>', methods=['GET', 'POST'])
@dec_check_session()
def traitValidation(sess, trialId, traitId):
#===========================================================================
# Page to display/modify validation parameters for a trait.
# Currently only relevant for integer traits.
#
    trial = dbUtil.GetTrial(sess, trialId)
    trt = dbUtil.GetTrait(sess, traitId)
    title = 'Trial: ' + trial.name + ', Trait: ' + trt.caption
    comparatorCodes = [
        ["gt", "Greater Than", 1],
        ["ge", "Greater Than or Equal to", 2],
        ["lt", "Less Than", 3],
        ["le", "Less Than or Equal to", 4]
    ]
    if request.method == 'GET':
        if trt.type == 0:
            tti = models.GetTrialTraitIntegerDetails(sess.DB(), traitId, trialId)
            minText = ""
            if tti and tti.min is not None:
                minText = "value='{0}'".format(tti.min)
            maxText = ""
            if tti and tti.max is not None:
                maxText = "value='{0}'".format(tti.max)
            bounds = "<p>Minimum: <input type='text' name='min' {0}>".format(minText)
            bounds += "<p>Maximum: <input type='text' name='max' {0}><br>".format(maxText);

            # Parse condition string, if present, to retrieve comparator and attribute.
            # Format of the string is: ^. <2_char_comparator_code> att:<attribute_id>$
            # The only supported comparison at present is comparing the score to a
            # single attribute.
            # NB, this format needs to be in sync with the version on the app. I.e. what
            # we save here, must be understood on the app.
            atId = -1
            if tti and tti.cond is not None:
                tokens = tti.cond.split()  # [["gt", "Greater than", 0?], ["ge"...]]?
                if len(tokens) == 3:
                    op = tokens[1]
                    atClump = tokens[2]
                    atId = int(atClump[4:])

            # Show available comparison operators:
            valOp = '<select name="validationOp">'
            valOp += '<option value="0">&lt;Choose Comparator&gt;</option>'
            for c in comparatorCodes:
                valOp += '<option value="{0}" {2}>{1}</option>'.format(
                    c[2], c[1], 'selected="selected"' if op == c[0] else "")
            # valOp += '<option value="1">Greater Than</option>'
            # valOp += '<option value="2">Greater Than or Equal to</option>'
            # valOp += '<option value="3">Less Than</option>'
            # valOp += '<option value="4">Less Than or Equal to</option>'
            valOp += '</select>'

            # Attribute list:
            attListHtml = '<select name="attributeList">'
            attListHtml += '<option value="0">&lt;Choose Attribute&gt;</option>'
            atts = dbUtil.GetTrialAttributes(sess, trialId)
            for att in atts:
                #if att.datatype = 0:  # MFK should restrict to int attributes
                attListHtml += '<option value="{0}" {2}>{1}</option>'.format(
                    att.id, att.name, "selected='selected'" if att.id == atId else "")
            attListHtml += '</select>'

            conts = 'Trial: ' + trial.name
            conts += '<br>Trait: ' + trt.caption
            conts += '<br>Type: ' + models.TRAIT_TYPE_NAMES[trt.type]
            conts += bounds
            conts += '<p>Integer traits can be validated by comparison with an attribute:'
            conts += '<br>Trait value should be ' + valOp + attListHtml
            conts += '<p><input type="button" style="color:red" value="Cancel" onclick="history.back()"><input type="submit" style="color:red" value="Submit">'

            return render_template('genericPage.html', content=HtmlForm(conts, post=True), title='Trait Validation')
        return render_template('genericPage.html', content='No validation for this trait type', title=title)
    if request.method == 'POST':
        op = request.form.get('validationOp')
        # if op == "0":
        #     return "please choose a comparator"
        at = request.form.get('attributeList')
        # if int(at) == 0:
        #     return "please choose an attribute"
        vmin = request.form.get('min')
        if len(vmin) == 0:
            vmin = None
        vmax = request.form.get('max')
        if len(vmax) == 0:
            vmax = None
        # Get existing trialTraitInteger, if any.
        tti = models.GetTrialTraitIntegerDetails(sess.DB(), traitId, trialId)
        newTTI = tti is None
        if newTTI:
            tti = models.TrialTraitInteger()
        tti.trial_id = trialId
        tti.trait_id = traitId
        tti.min = vmin
        tti.max = vmax
        if int(op) > 0 and int(at) > 0:
            tti.cond = ". " + comparatorCodes[int(op)-1][0] + ' att:' + at
        if newTTI:
            sess.DB().add(tti)
        sess.DB().commit()
        return render_template('genericPage.html', content=TrialHtml(sess, trialId), title='Trial Data')


@app.route('/', methods=["GET", "POST"])
def main():
#-----------------------------------------------------------------------
# Entry point for FieldPrime web admin.
# Without arguments it presents a login screen. 
# As a POST (without an operation), it process the login data.
# With an operation ("op" argument), it processes the operation.
#
# Note we could have different urls for operations, but at the moment this
# is a quick port from a non-flask version, and this is the way it initially implemented.
#
# Note the use of sessions. On login, a server side session is established (state is stored
# in the file system), and the id of this session is sent back to the browser in a cookie,
# which should be sent back with each subsequent request.
#
#
#
    COOKIE_NAME = 'sid'
    sid = request.cookies.get(COOKIE_NAME)                # Get the session id from cookie (if there)
    sess = websess.WebSess(False, sid, LOGIN_TIMEOUT, app.config['SESS_FILE_DIR'])     # Create session object (may be existing session)
    g.rootUrl = url_for(sys._getframe().f_code.co_name)   # Set global variable accessible by templates (to the url for this func)
    op = request.args.get('op', '')
    if not op:
        error = ""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            if not username:
                error = 'No username'
            elif not password:
                error = 'No password'
            elif not CheckPassword(username, password):
                error = 'Invalid password'
            else:
                # Good to go, show the user front page:
                sess.resetLastUseTime()
                sess.SetUserDetails(username, password)
                resp = FrontPage(sess)
                resp.set_cookie(COOKIE_NAME, sess.sid())
                return resp

        #return render_template('login.html', msg = error, title='Field Prime Login')
        return LoginForm(error)

    #----------------------------------------------------------
    # Case operation is specified:
    #

    # Check session still valid:
    if not sess.Valid():
        # Present login form:
        # Ideally have a redirect after login to current op, if there is one, but would need all form parameters
        # to be passed thru to the login form (op and any others needed for op, such as tid), and then passed
        # back by the login form to the login form submit handler. Alternatively perhaps, could bundle the
        # parameters into the session shelf.
        return render_template('login.html', title='Field Prime Login')

    if op == 'addSysTrait2Trial':
        tid = request.args.get('tid')
        errMsg = AddSysTraitTrial(sess, tid, request.form['traitID'])
        if errMsg:
            return render_template('genericPage.html', content=errMsg, title='Error')
        # If all is well, display the trial page:
        return render_template('genericPage.html', content=TrialHtml(sess, tid), title='Trial Data')

    elif op == 'user':
        return AdminForm(sess)
    elif op == 'newpw' or op == 'setAppPassword':
        return ProcessAdminForm(sess, op, request.form)

    elif op == 'newTrial':
        return fpTrial.NewTrial(sess)

    elif op == 'createTrial':
        uploadFile = request.files['file']
        res = fpTrial.CreateTrial(sess, uploadFile, request.form)
        if res:
            return res
        return FrontPage(sess)

    elif op == 'newTrait':
        # NB, could be a new sys trait, or trait for a trial. Indicated by tid which will be
        # either 'sys' or the trial id respectively.
        return render_template('newTrait.html', trialId = request.args.get("tid"),
                               traitTypes = models.TRAIT_TYPE_TYPE_IDS, title='New Trait')
    elif op == 'createTrait':
        trialId = request.args.get("tid")
        errMsg = CreateNewTrait(sess, trialId, request)
        if errMsg:
            return render_template('genericPage.html', content=errMsg, title='Error')

        if trialId == 'sys':
            return FrontPage(sess)
        return render_template('genericPage.html', content=TrialHtml(sess, trialId), title='Trial Data')

    elif op == 'traitValidation':
        trialId = request.args.get("tid")
        errMsg = TraitValidation(sess, trialId, request)
        if errMsg:
            return render_template('genericPage.html', content=errMsg, title='Error')
        return render_template('genericPage.html', content=TrialHtml(sess, tid), title='Trial Data')

    elif op == 'traitInstance':
        return render_template('genericPage.html',
                               content=TraitInstanceHtml(sess, request.args.get("tid")),
                               title='Trait Instance Data')

    elif op == 'home': # MFK - might be good to have separate URL for homepage .../user/<username> 
        return FrontPage(sess)

    else:
        return render_template('genericPage.html', content="No such operation ({0})".format(op), title='Error')


##############################################################################################################


def LogDebug(hdr, text):
#-------------------------------------------------------------------------------------------------
# Writes stuff to file system (for debug) - not routinely used..
    f = open('/tmp/fieldPrimeDebug','a')
    print >>f, "--- " + hdr + ": ---"
    print >>f, text
    print >>f, "------------------"
    f.close


# For local testing:
if __name__ == '__main__':
    app.config['SESS_FILE_DIR'] = '/home/***REMOVED***/fpserver/fpa/fp_web_admin/tmp2'
    app.run(debug=True, host='0.0.0.0')

