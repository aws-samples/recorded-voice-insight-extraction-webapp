# Example typescript project with basic functionalities

### Typescript
* Typescript is a superset of JavaScript and sahres the same syntax and structure as JS, but it allows you to specify variable types, return types, etc.
* TypeScript aims to enhance the development experience and catch errors at compile-time, leading to more robust and maintainable code. 
* It gets compiled into JavaScript before you run it.

### Installation
1. Install Node.js and npm
2. `cd typescript-hello-world`
3. `npm init -y` (this creates package.json)
4. Install typescript: `npm install typescript --save-dev` (this creates package-lock.json, and node_modules dir)
5. Create a typescript file (my-source-dir/hello-world.ts) that logs to console or something
6. Create a `tsconfig.json` file (sets compiler options, tells compiler source code lives in my-source-dir, where to put source codeetc)
7. Compile the code with `npx tsc` (compiles the source code into a .js file, puts it in output directory)
8. Run the javascript code with `node my-compiled-code/hello-world.js`