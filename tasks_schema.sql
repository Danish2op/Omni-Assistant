CREATE TABLE tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name TEXT NOT NULL,
    due_date TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium'
);
