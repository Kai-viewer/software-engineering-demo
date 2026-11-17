CREATE TABLE users (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('author', 'editor'))
);

CREATE TABLE submissions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES users(id),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('編輯中', '審查中', '已通過'))
);

-- 示範密碼都是 pass1234；正式使用前請更換。
INSERT INTO users (username, password_hash, name, role) VALUES
    ('author', '7e879fd082c0758de63e567503209d33$be06faf70e2282d37264cc61558488a310c19d130a04d813c0c78fcd62a2a448', '作者', 'author'),
    ('editor', '96c1f43d851ba6bcada6bd0558f948ee$c0f4a7e8adc09c86791ac7acedb65e10e5e4ca913daf29a41f4a48f3ac834d6f', '編輯', 'editor');
