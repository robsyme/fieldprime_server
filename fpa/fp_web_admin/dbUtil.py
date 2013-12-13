# dbUtil.py
# Michael Kirk 2013
#
#
#


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fp_common.models import Trial, Trait, TrialUnit, TrialUnitAttribute, \
    AttributeValue, TraitInstance, Datum, TrialUnitNote, SYSTYPE_SYSTEM

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation


#-- CONSTANTS: ---------------------------------------------------------------------


def GetEngine(sess):
#-----------------------------------------------------------------------
# This should be called once only and the result stored,
# currently done in session module.
#
    fpUser = 'fp_' + sess.GetUser()
    engine = create_engine('mysql://{0}:{1}@localhost/{2}'.format(fpUser, sess.GetPassword(), fpUser))
    Session = sessionmaker(bind=engine)
    dbsess = Session()
    return dbsess

def GetEngineForApp(user, pw, targetUser):
#-----------------------------------------------------------------------
# This should be called once only and the result stored,
# currently done in session module.
#
    dbname = 'fp_' + targetUser
    engine = create_engine('mysql://{0}:{1}@localhost/{2}'.format(user, pw, dbname))
    Session = sessionmaker(bind=engine)
    dbsess = Session()
    return dbsess

def GetTrials(sess):
    return sess.DB().query(Trial).all()

def GetTrial(sess, trialID):
    return sess.DB().query(Trial).filter(Trial.id == trialID).one()

def GetTrait(sess, traitId):
    return sess.DB().query(Trait).filter(Trait.id == traitId).one()

def GetTrialFromDBsess(sess, trialID):
    return sess.DB().query(Trial).filter(Trial.id == trialID).one()

def GetTraitInstancesForTrial(sess, trialID):
    return sess.DB().query(TraitInstance).filter(TraitInstance.trial_id == trialID).all()

def GetTrialAttributes(sess, trialID):
    return sess.DB().query(TrialUnitAttribute).filter(TrialUnitAttribute.trial_id == trialID).all()

def GetTrialUnits(sess, trialID):
    return sess.DB().query(TrialUnit).filter(TrialUnit.trial_id == trialID).all()

def GetDatum(sess, trialUnit_id, traitInstance_id):
    return sess.DB().query(Datum).filter(and_(Datum.trialUnit_id == trialUnit_id, Datum.traitInstance_id == traitInstance_id)).all()

def GetSysTraits(sess):
    return sess.DB().query(Trait).filter(Trait.sysType == SYSTYPE_SYSTEM).all()

def GetTrialUnitNotes(sess, trialUnit_id):
    return sess.DB().query(TrialUnitNote).filter(TrialUnitNote.trialUnit_id == trialUnit_id).all()
