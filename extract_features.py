""" This file processes an .eml file and generates a Feature file of the
form:

    >>> metadata_file, payload_file = generate_files(test_email)
    >>> print(payload_file)
    ... // SPAM from <file_name>
    ... 1
    ... // Begin payload
    ... metadata word 1
    ... ...
    ... metadata word q
    ... payload word 1
    ... ...
    ... payload word p

    Where a "word" is either a space-separated word n-gram or character n-gram.
    See the `parse_email` documentation for output options.
"""
import email
import bs4


# Disable UserWarnings from beautifulsoup
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')


stop_words = """
a
about
above
across
after
again
against

all

almost

alone

along

already

also

although

always

among

an

and

another

any

anybody

anyone

anything

anywhere

are

area

areas

around

as

ask

asked

asking

asks

at

away

b

back

backed

backing

backs

be

became

because

become

becomes

been

before

began

behind

being

beings

best

better

between

big

both

but

by

c

came

can

cannot

case

cases

certain

certainly

clear

clearly

come

could

d

did

differ

different

differently

do

does

done

down

down

downed

downing

downs

during

e

each

early

either

end

ended

ending

ends

enough

even

evenly

ever

every

everybody

everyone

everything

everywhere

f

face

faces

fact

facts

far

felt

few

find

finds

first

for

four

from

full

fully

further

furthered

furthering

furthers

g

gave

general

generally

get

gets

give

given

gives

go

going

good

goods

got

great

greater

greatest

group

grouped

grouping

groups

h

had

has

have

having

he

her

here

herself

high

high

high

higher

highest

him

himself

his

how

however

i

if

important

in

interest

interested

interesting

interests

into

is

it

its

itself

j

just

k

keep

keeps

kind

knew

know

known

knows

l

large

largely

last

later

latest

least

less

let

lets

like

likely

long

longer

longest

m

made

make

making

man

many

may

me

member

members

men

might

more

most

mostly

mr

mrs

much

must

my

myself

n

necessary

need

needed

needing

needs

never

new

new

newer

newest

next

no

nobody

non

noone

not

nothing

now

nowhere

number

numbers

o

of

off

often

old

older

oldest

on

once

one

only

open

opened

opening

opens

or

order

ordered

ordering

orders

other

others

our

out

over

p

part

parted

parting

parts

per

perhaps

place

places

point

pointed

pointing

points

possible

present

presented

presenting

presents

problem

problems

put

puts

q

quite

r

rather

really

right

right

room

rooms

s

said

same

saw

say

says

second

seconds

see

seem

seemed

seeming

seems

sees

several

shall

she

should

show

showed

showing

shows

side

sides

since

small

smaller

smallest

so

some

somebody

someone

something

somewhere

state

states

still

still

such

sure

t

take

taken

than

that

the

their

them

then

there

therefore

these

they

thing

things

think

thinks

this

those

though

thought

thoughts

three

through

thus

to

today

together

too

took

toward

turn

turned

turning

turns

two

u

under

until

up

upon

us

use

used

uses

v

very

w

want

wanted

wanting

wants

was

way

ways

we

well

wells

went

were

what

when

where

whether

which

while

who

whole

whose

why

will

with

within

without

work

worked

working

works

would

x

y

year

years

yet

you

young

younger

youngest

your

yours

z""".split()


def generate_files(out_fname_template, email_fnames, label_file,
                   include_html=True,  # use bs4
                   case_insensitive=False,  # call .lower()
                   n_gram_lengths=[1],
                   normalize_whitespace=True,  # call ' '.join(.split())
                   by_character=False  # call .split() or not
                   ):
    labels = dict()
    with open(label_file) as f:
        for label in f:
            w = label.split(maxsplit=1)
            if len(w) < 2:
                continue
            labels[w[1][:-1]] = w[0]

    for i, eml in enumerate(email_fnames):
        short_name = 'TRAIN_' + eml.split('TRAIN_')[-1]

        is_spam = labels.get(short_name, None)

        if True or i % (len(email_fnames) // 10) == 0:
            print('Processing', eml, 'aka', short_name, 'spam or ham:', is_spam)

        datum = parse_email(
            eml,
            include_html,
            case_insensitive,
            n_gram_lengths,
            normalize_whitespace,
            by_character,
            is_spam=is_spam)
        with open(out_fname_template.format(i), 'w') as f:
            # TODO change? write label somewhere else?
            f.write(is_spam + '\n')
            f.write('// {} email derived from {}\n'.format(
                    'spam' if is_spam else 'ham', eml))
            f.write('// Begin payload\n')
            for w in datum['payload']:
                f.write(w + '\n')


def ngrams(words, lengths, joiner=' '):
    return [joiner.join(words[i + j]
                        for j in range(n))
            for i, c in enumerate(words)
            for n in lengths if i + n < len(words) and words[i].lower() not in stop_words
            ]


def get_text(m):
    if type(m) is str:
        return m
    if type(m) is bytes:
        return m
    if m.is_multipart():
        return get_text(m.get_payload(0))
    else:
        return m.get_payload()


def parse_email(email_fname,
                include_html=True,
                case_insensitive=False,
                n_gram_lengths=[1, 2],
                normalize_whitespace=True,
                by_character=False,
                is_spam=False,
                ):

    # Open email file
    m = email.parser.BytesParser().parse(open(email_fname, 'rb'))
    datum = {'from': m['From'],
             'subject': m['Subject'],  # TODO how to get text?
             'spam': is_spam
             }
    if datum['subject'] is None:
        datum['subject'] = ''
    if type(datum['subject']) is email.header.Header:
        datum['subject'] = datum['subject'].encode()

    payload = ''

    # If desired, strip payload of HTML tags
    if include_html:
        payload = get_text(m)
    else:
        payload = bs4.BeautifulSoup(get_text(m), 'lxml').getText()

    payload = datum['subject'] + '\n\n' + payload

    # If desired, force case
    if case_insensitive:
        payload = payload.lower()

    # If desired, convert each sequence of whitespace to a single space
    if normalize_whitespace:
        payload = ' '.join(payload.split())

    # If desired, convert the payload into a list of whitespace separated words
    if not by_character:
        payload = payload.split()

    # Compute n-grams
    datum['payload'] = ngrams(payload, n_gram_lengths,
                              '' if by_character else ' ')

    # Check for missing fields
    for k in datum:
        if datum[k] is None:
            print('Email', email_fname, 'is missing the header', k)

    # Get useful metadata
    datum['date'] = m['Date']
    return datum


# Load 1000 emails from CSDMC2010 dataset
output = 'data/payload{}.data'
emails = ["spam/CSDMC2010_SPAM/TRAINING/TRAIN_{:05d}.eml".format(i) for i in range(4326 + 1)]
labels = 'spam/CSDMC2010_SPAM/SPAMTrain.label'
# TODO generate_files should do as much as possible with each open .eml
# only all it once
generate_files(output, emails, labels,
               include_html=False,
               case_insensitive=True,
               n_gram_lengths=[1],
               by_character=False)

generate_files('data/char{}.data', emails, labels,
               include_html=True,
               case_insensitive=False,
               n_gram_lengths=[4],
               by_character=True)
