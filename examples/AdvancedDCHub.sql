CREATE TABLE accounts (
nick TEXT UNIQUE,
password TEXT DEFAULT '',
args TEXT DEFAULT '',
op INTEGER DEFAULT 0,
verified INTEGER DEFAULT 0,
creationtime INTEGER
);

CREATE TABLE events (
accountid INTEGER,
eventtypeid INTEGER,
noteby INTEGER,
time INTEGER,
note TEXT
);

CREATE TABLE eventtypes (
name TEXT
);

CREATE TABLE activeevents (
eventtypeid INTEGER,
entry TEXT,
until INTEGER,
UNIQUE (eventtypeid, entry)
);

CREATE TABLE torrents (
active INTEGER DEFAULT 0,
addedby INTEGER,
approvalby INTEGER,
addedtime INTEGER,
approvaltime INTEGER,
location TEXT UNIQUE,
description TEXT
);

CREATE INDEX accountid_eventtypeid_idx ON events (accountid, eventtypeid);
CREATE INDEX eventtypeid_note_idx ON events(eventtypeid, note);
CREATE INDEX active_idx ON torrents (active);

INSERT INTO eventtypes (name) VALUES ('join');
INSERT INTO eventtypes (name) VALUES ('');
INSERT INTO eventtypes (name) VALUES ('ban');
INSERT INTO eventtypes (name) VALUES ('silence');
INSERT INTO eventtypes (name) VALUES ('stupidify');
INSERT INTO eventtypes (name) VALUES ('verify');
INSERT INTO eventtypes (name) VALUES ('note');

-- INSERT INTO accounts (nick, password, args, op, verified, creationtime) VALUES ('yournick', 'yourpass', 'yourargs', 1, 1, 1);
