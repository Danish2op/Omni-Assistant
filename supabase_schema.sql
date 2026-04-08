CREATE TABLE knowledge_base (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    category TEXT,
    content TEXT,
    metadata JSONB
);
