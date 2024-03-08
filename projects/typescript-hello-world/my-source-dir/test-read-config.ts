import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as path from 'path';
import { ConfigData } from './my-config-types';

// Cfg file always one directory up from this typescript file
const cfgPath: string = path.resolve(__dirname, '..', 'config.yml');
const fileContents = fs.readFileSync(cfgPath, 'utf8');
const data: ConfigData = yaml.load(fileContents) as ConfigData;

console.log(data.block1.var2);