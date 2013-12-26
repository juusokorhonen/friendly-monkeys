drop table if exists monkeys;
create table monkeys (
	monkeyid integer primary key autoincrement,
	username text not null,
	name text not null,
	unique (username)
);
drop table if exists friendships;
create table friendships (
	nodeid integer primary key autoincrement,
	monkeyid1 integer not null,
	monkeyid2 integer not null
);

