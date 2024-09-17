# Content for item 0

```markdown
Auth

# Use Supabase Auth with Next.js

## Learn how to configure Supabase Auth for the Next.js App Router.

* * *

1

### Create a new Supabase project

Head over to [database.new](https://database.new) and create a new Supabase project.

Your new database has a table for storing your users. You can see that this table is currently empty by running some SQL in the [SQL Editor](https://supabase.com/dashboard/project/_/sql/new).

SQL\_EDITOR

`
_10
select * from auth.users;
`

2

### Create a Next.js app

Use the `create-next-app` command and the `with-supabase` template, to create a Next.js app pre-configured with:

- [Cookie-based Auth](https://supabase.com/docs/guides/auth/auth-helpers/nextjs)
- [TypeScript](https://www.typescriptlang.org/)
- [Tailwind CSS](https://tailwindcss.com/)

[See GitHub repo](https://github.com/vercel/next.js/tree/canary/examples/with-supabase)

Terminal

`
_10
npx create-next-app -e with-supabase
`

3

### Declare Supabase Environment Variables

Rename `.env.local.example` to `.env.local` and populate with [your project's URL and Anon Key](https://supabase.com/dashboard/project/_/settings/api).

.env.local

`
_10
NEXT_PUBLIC_SUPABASE_URL=your-project-url
_10
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
`

4

### Start the app

Start the development server, go to [http://localhost:3000](http://localhost:3000) in a browser, and you should see the contents of `app/page.tsx`.

To Sign Up a new user, navigate to [http://localhost:3000/login](http://localhost:3000/login), and click `Sign Up Now`.

Check out the [Supabase Auth docs](https://supabase.com/docs/guides/auth#authentication) for more authentication methods.

Terminal

`
_10
npm run dev
`
```

----
