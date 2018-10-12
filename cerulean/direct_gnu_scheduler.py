from cerulean.job_description import JobDescription
from cerulean.job_status import JobStatus
from cerulean.scheduler import Scheduler
from overrides import overrides


class DirectGnuScheduler(Scheduler):
    """A scheduler that runs processes directly on a GNU system.

    This scheduler does not have a queue, instead it launches each \
    job immediately as a process, and uses ps and kill to manage it. \

    Args:
        terminal: The terminal to execute on.
    """

    def __init__(self, terminal):
        self.__terminal = terminal

    @overrides
    def submit_job(self, job_description: JobDescription) -> str:
        if job_description.command is None:
            raise ValueError('Job description is missing a command')

        if job_description.mpi_processes_per_node is not None:
            raise RuntimeError(
                "mpi_processes_per_node is not supported by DirectGnuScheduler, "
                "because we cannot inject this into the MPI configuration in an environment "
                "without a scheduler. You should call mpirun with an appropriate parameter "
                "instead.")

        job_script = ''
        for name, value in job_description.environment.items():
            job_script += "export {}='{}'\n".format(name, value)
        if job_description.working_directory is not None:
            job_script += 'cd {}\n'.format(job_description.working_directory)
        job_script += 'exit_code_file=$(mktemp)\n'
        # TODO: use ulimit to set a timeout
        job_script += "(\n"
        if job_description.time_reserved is not None:
            job_script += "ulimit -t {}\n".format(
                job_description.time_reserved)
        escaped_command = job_description.command.replace("'", "'\\\''")
        escaped_args = map(lambda s: s.replace("'", "'\\\''"),
                           job_description.arguments)
        job_script += "bash -c '"
        job_script += '{}'.format(escaped_command)
        job_script += ' {}'.format(' '.join(escaped_args))
        if job_description.stdout_file is not None:
            job_script += ' >{}'.format(job_description.stdout_file)
        if job_description.stderr_file is not None:
            job_script += ' 2>{}'.format(job_description.stderr_file)
        job_script += "' ; "
        job_script += 'echo $? >$exit_code_file'
        job_script += ') >/dev/null 2>/dev/null &\n'
        job_script += 'echo -n $! $exit_code_file\n'
        job_script += 'disown\n'

        print('Job script: {}'.format(job_script))
        exit_code, output, error = self.__terminal.run(10.0, 'bash', [],
                                                       job_script)

        return output

    @overrides
    def get_status(self, job_id: str) -> JobStatus:
        pid = job_id.split(' ')[0]
        exit_code, output, error = self.__terminal.run(10.0, 'ps', ['-p', pid])

        if exit_code == 0:
            return JobStatus.RUNNING
        else:
            return JobStatus.DONE

    @overrides
    def get_exit_code(self, job_id: str) -> int:
        exit_code_file = job_id.split(' ', maxsplit=1)[1]
        exit_code, output, error = self.__terminal.run(10.0, 'cat',
                                                       [exit_code_file])
        # TODO: delete tempfile?
        try:
            return int(output)
        except ValueError:
            return None

    @overrides
    def cancel(self, job_id: str) -> None:
        pid = job_id.split(' ')[0]
        exit_code, output, error = self.__terminal.run(10.0, 'kill', [pid])
        # TODO: Check exit code and return whether it was running?
        # TODO: Check if it's stopped, do a -9 if not?
        pass