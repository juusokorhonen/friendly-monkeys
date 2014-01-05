drop table if exists monkeys;
create table monkeys (
	id integer primary key autoincrement,
	username text not null,
	name text not null,
	unique (username)
);
drop table if exists friendships;
create table friendships (
	nodeid integer primary key autoincrement,
	id1 integer not null,
	id2 integer not null
);

