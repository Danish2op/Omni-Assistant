CREATE TABLE knowledge_base (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    category TEXT,
    content TEXT,
    metadata JSONB
);

-- Routines table (actual schema as of 2026-05-13)
CREATE TABLE routines (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL,
    parameters JSONB,
    frequency TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);
