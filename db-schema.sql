-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.restaurants (
  id integer NOT NULL DEFAULT nextval('restaurants_id_seq'::regclass),
  name character varying NOT NULL,
  city character varying,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT restaurants_pkey PRIMARY KEY (id)
);
CREATE TABLE public.branches (
  id integer NOT NULL DEFAULT nextval('branches_id_seq'::regclass),
  name character varying NOT NULL,
  restaurant_id integer NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT branches_pkey PRIMARY KEY (id),
  CONSTRAINT branches_restaurant_id_fkey FOREIGN KEY (restaurant_id) REFERENCES public.restaurants(id)
);
CREATE TABLE public.personnel (
  id integer NOT NULL DEFAULT nextval('managers_id_seq'::regclass),
  restaurant_id integer NOT NULL,
  branch_id integer NOT NULL,
  full_name character varying NOT NULL,
  telegram_id bigint UNIQUE,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  phone_number character varying,
  role_name text NOT NULL DEFAULT 'manager'::text,
  CONSTRAINT personnel_pkey PRIMARY KEY (id),
  CONSTRAINT managers_restaurant_id_fkey FOREIGN KEY (restaurant_id) REFERENCES public.restaurants(id),
  CONSTRAINT managers_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(id)
);
CREATE TABLE public.task_templates (
  id integer NOT NULL DEFAULT nextval('task_templates_id_seq'::regclass),
  restaurant_id integer NOT NULL,
  branch_id integer NOT NULL,
  title character varying NOT NULL,
  description text,
  frequency character varying NOT NULL DEFAULT 'daily'::character varying CHECK (frequency::text = ANY (ARRAY['daily'::character varying, 'weekly'::character varying, 'monthly'::character varying]::text[])),
  due_time time without time zone,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  personnel_id integer,
  CONSTRAINT task_templates_pkey PRIMARY KEY (id),
  CONSTRAINT task_templates_restaurant_id_fkey FOREIGN KEY (restaurant_id) REFERENCES public.restaurants(id),
  CONSTRAINT task_templates_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(id),
  CONSTRAINT task_templates_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id)
);
CREATE TABLE public.task_instances (
  id integer NOT NULL DEFAULT nextval('task_instances_id_seq'::regclass),
  template_id integer NOT NULL,
  personnel_id integer NOT NULL,
  restaurant_id integer NOT NULL,
  branch_id integer NOT NULL,
  scheduled_date date NOT NULL,
  due_at timestamp with time zone,
  completed boolean DEFAULT false,
  completed_at timestamp with time zone,
  note text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT task_instances_pkey PRIMARY KEY (id),
  CONSTRAINT task_instances_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.task_templates(id),
  CONSTRAINT task_instances_restaurant_id_fkey FOREIGN KEY (restaurant_id) REFERENCES public.restaurants(id),
  CONSTRAINT task_instances_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(id),
  CONSTRAINT task_instances_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id)
);
CREATE TABLE public.kpi_summaries (
  id integer NOT NULL DEFAULT nextval('kpi_summaries_id_seq'::regclass),
  personnel_id integer NOT NULL,
  restaurant_id integer NOT NULL,
  branch_id integer NOT NULL,
  period_type character varying NOT NULL CHECK (period_type::text = ANY (ARRAY['daily'::character varying, 'weekly'::character varying, 'monthly'::character varying]::text[])),
  period_start date NOT NULL,
  period_end date NOT NULL,
  total_tasks integer NOT NULL DEFAULT 0,
  completed_tasks integer NOT NULL DEFAULT 0,
  completion_rate numeric,
  calculated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT kpi_summaries_pkey PRIMARY KEY (id),
  CONSTRAINT kpi_summaries_restaurant_id_fkey FOREIGN KEY (restaurant_id) REFERENCES public.restaurants(id),
  CONSTRAINT kpi_summaries_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(id),
  CONSTRAINT kpi_summaries_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id)
);