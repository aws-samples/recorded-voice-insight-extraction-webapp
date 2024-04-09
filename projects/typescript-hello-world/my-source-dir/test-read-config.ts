import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as path from 'path';
import { ConfigData, defaultConfigData } from './my-config-types';

// Cfg file always one directory up from this typescript file
const cfgPath: string = path.resolve(__dirname, '..', 'config.yml');
const fileContents = fs.readFileSync(cfgPath, 'utf8');
const userConfig: ConfigData = yaml.load(fileContents) as ConfigData;

// Merge userConfig with default values
const mergedConfig: ConfigData = {
    ...defaultConfigData,
    ...userConfig,
};

console.log(mergedConfig.block1.var2)
console.log(mergedConfig.var3)
console.log(mergedConfig)